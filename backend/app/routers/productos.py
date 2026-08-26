import io

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, get_usuario_actual, requerir_supervisor
from app.database import get_db
from app.models.producto import ProductoFamilia
from app.schemas.producto import CargaCatalogoResumen, FamiliaOut, ProductoFamiliaOut

router = APIRouter(prefix="/catalogo-productos", tags=["catalogo-productos"])

COLUMNAS_REQUERIDAS = ["Codigo", "Descripcion", "familia_id", "FamiliaDesc", "Baja"]


def _parsear_mantenedor(contenido: bytes) -> list[ProductoFamilia]:
    """Parsea el 'MANTENEDOR_DE_PRODUCTOS' tal cual lo exporta el ERP: una
    fila por producto, con las columnas Codigo/Descripcion/familia_id/
    FamiliaDesc/Baja en cualquier posición (se ubican por nombre de
    encabezado en la primera fila)."""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True, read_only=True)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pude leer el archivo .xlsx") from exc

    ws = wb.worksheets[0]
    filas = ws.iter_rows(values_only=True)
    encabezados = [str(h).strip() if h is not None else "" for h in next(filas)]
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in encabezados]
    if faltantes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Al archivo le faltan columnas esperadas: {', '.join(faltantes)}",
        )
    idx = {h: i for i, h in enumerate(encabezados)}

    productos: list[ProductoFamilia] = []
    vistos: set[str] = set()
    for fila in filas:
        if not fila or fila[idx["Codigo"]] is None:
            continue
        codigo = str(fila[idx["Codigo"]]).strip()
        if not codigo or codigo in vistos:
            continue
        vistos.add(codigo)
        descripcion = fila[idx["Descripcion"]]
        familia_id = fila[idx["familia_id"]]
        familia_desc = fila[idx["FamiliaDesc"]]
        familia_desc = str(familia_desc).strip() if familia_desc else None
        if familia_desc in ("", "No definido"):
            familia_desc = None
        baja = fila[idx["Baja"]]
        productos.append(
            ProductoFamilia(
                codigo=codigo,
                descripcion=str(descripcion).strip() if descripcion else "",
                familia_id=int(familia_id) if familia_id is not None else None,
                familia_desc=familia_desc,
                baja=bool(baja),
            )
        )
    return productos


@router.post("/importar", response_model=CargaCatalogoResumen)
async def importar_catalogo(
    archivo: UploadFile,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Reemplaza por completo el catálogo de productos/familias (mismo
    patrón que las demás cargas: borra lo anterior y sube la lista nueva)."""
    contenido = await archivo.read()
    productos = _parsear_mantenedor(contenido)
    if not productos:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo no tiene productos")

    await db.execute(delete(ProductoFamilia))
    db.add_all(productos)
    await db.commit()

    familias = {p.familia_desc for p in productos if p.familia_desc}
    sin_familia = sum(1 for p in productos if not p.familia_desc)
    return CargaCatalogoResumen(total_productos=len(productos), total_familias=len(familias), sin_familia=sin_familia)


@router.get("", response_model=list[ProductoFamiliaOut])
async def listar_catalogo(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    result = await db.execute(select(ProductoFamilia).order_by(ProductoFamilia.codigo))
    return result.scalars().all()


@router.get("/familias", response_model=list[FamiliaOut])
async def listar_familias(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Listado de familias de productos (id + descripción) para que
    cualquier vendedor pueda elegir qué familias proyectar, sin necesitar
    acceso al catálogo completo (reservado a supervisor/admin)."""
    result = await db.execute(
        select(ProductoFamilia.familia_id, ProductoFamilia.familia_desc)
        .where(ProductoFamilia.familia_id.is_not(None), ProductoFamilia.baja.is_(False))
        .distinct()
        .order_by(ProductoFamilia.familia_desc)
    )
    return [FamiliaOut(familia_id=fid, familia_desc=desc) for fid, desc in result.all()]
