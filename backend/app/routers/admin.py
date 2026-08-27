import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, requerir_admin, requerir_cargador
from app.database import get_db
from app.models.objetivo import ObjetivoMensual
from app.schemas.admin import ObjetivoIn, ObjetivoOut, ResumenImportacionOut
from app.services.importers import (
    aplicar_clientes_zona,
    aplicar_ventas,
    aplicar_visitas,
    parse_clientes_zona_xls,
    parse_ventas_xls,
    parse_visitas_html,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/objetivos", response_model=ObjetivoOut, status_code=status.HTTP_201_CREATED)
async def asignar_objetivo(
    body: ObjetivoIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    """Asigna (o actualiza) el objetivo de venta mensual de un vendedor."""
    stmt = (
        pg_insert(ObjetivoMensual)
        .values(vendedor_codigo=body.vendedor_codigo, anio=body.anio, mes=body.mes, monto=body.monto)
        .on_conflict_do_update(
            index_elements=["vendedor_codigo", "anio", "mes"],
            set_={"monto": body.monto},
        )
        .returning(ObjetivoMensual)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()


@router.post("/ventas/importar", response_model=ResumenImportacionOut)
async def importar_ventas(
    archivo: UploadFile,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_cargador),
):
    """Carga el reporte 'Detalle de comprobantes por cliente' de Axum (.xls).

    Reemplaza lo ya cargado para cada combinación (vendedor, fecha) presente
    en el archivo -- reimportar el mismo reporte es seguro. Vendedores, zonas
    y clientes que aparezcan por primera vez se dan de alta automáticamente
    con los datos mínimos del reporte."""
    contenido = await archivo.read()
    try:
        lineas = parse_ventas_xls(contenido)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not lineas:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo no tiene líneas de venta")

    resumen = await aplicar_ventas(db, lineas)
    return resumen


@router.post("/visitas/importar", response_model=ResumenImportacionOut)
async def importar_visitas(
    archivo: UploadFile,
    fecha: datetime.date = Form(...),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_cargador),
):
    """Carga el recorrido diario de Axum (reporte_19): una fila por cliente
    proyectado, con horarios reales si fue visitado. Reemplaza por completo
    lo cargado para esa fecha. Clientes nuevos que aparezcan con una visita
    efectiva se dan de alta automáticamente."""
    contenido = await archivo.read()
    try:
        filas = parse_visitas_html(contenido)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not filas:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El reporte no tiene filas")

    resumen = await aplicar_visitas(db, fecha, filas)
    return resumen


@router.post("/clientes-zona/importar", response_model=ResumenImportacionOut)
async def importar_clientes_zona(
    archivo: UploadFile,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_cargador),
):
    """Carga el 'Listado de detalle de clientes activos' de Axum (.xls): el
    padrón completo de clientes con su zona y localidad. A diferencia de
    ventas/visitas, este listado SÍ pisa la zona de un cliente ya existente
    (es la fuente de verdad de zona/localidad)."""
    contenido = await archivo.read()
    try:
        filas = parse_clientes_zona_xls(contenido)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not filas:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El listado no tiene filas")

    resumen = await aplicar_clientes_zona(db, filas)
    return resumen
