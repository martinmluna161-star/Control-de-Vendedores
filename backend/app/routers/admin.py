import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, requerir_admin, requerir_cargador, requerir_supervisor
from app.models.objetivo import ObjetivoMensual, ObjetivoSugerido
from app.database import get_db
from app.schemas.admin import (
    ObjetivoIn,
    ObjetivoOut,
    ObjetivoSugeridoOut,
    ResumenImportacionOut,
    ResumenObjetivosSugeridosOut,
)
from app.services.importers import (
    aplicar_clientes_zona,
    aplicar_objetivos_sugeridos,
    aplicar_ventas,
    aplicar_visitas,
    parse_clientes_zona_xls,
    parse_objetivos_sugeridos_xlsx,
    parse_ventas_xls,
    parse_visitas_html,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/objetivos", response_model=ObjetivoOut, status_code=status.HTTP_201_CREATED)
async def asignar_objetivo(
    body: ObjetivoIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Asigna (o actualiza) el objetivo de venta mensual de un vendedor.
    Lo puede definir el supervisor de campo o el admin."""
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


@router.post("/objetivos/sugeridos/importar", response_model=ResumenObjetivosSugeridosOut)
async def importar_objetivos_sugeridos(
    archivo: UploadFile,
    anio: int = Form(...),
    mes: int = Form(...),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Carga la planilla de proyección de objetivos (real del mes anterior +
    objetivo sugerido para el mes nuevo) como referencia para que
    supervisor/admin definan el objetivo real de cada vendedor con
    ``POST /admin/objetivos``. Es exclusivamente informativo: no crea ni
    modifica ningún ``ObjetivoMensual`` por sí sola, y solo la ve supervisor/admin."""
    contenido = await archivo.read()
    try:
        filas = parse_objetivos_sugeridos_xlsx(contenido)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    filas_importadas = await aplicar_objetivos_sugeridos(db, anio, mes, filas)
    return ResumenObjetivosSugeridosOut(anio=anio, mes=mes, filas_importadas=filas_importadas)


@router.get("/objetivos/sugeridos", response_model=list[ObjetivoSugeridoOut])
async def listar_objetivos_sugeridos(
    anio: int = Query(...),
    mes: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Objetivos sugeridos de un período, para mostrar como referencia junto
    al formulario de objetivo real. Solo supervisor/admin."""
    result = await db.execute(
        select(ObjetivoSugerido).where(ObjetivoSugerido.anio == anio, ObjetivoSugerido.mes == mes)
    )
    return result.scalars().all()


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
