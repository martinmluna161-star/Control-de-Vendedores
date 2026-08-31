import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, get_usuario_actual, requerir_supervisor
from app.database import get_db
from app.models.desarrollo_cliente import DesarrolloClienteNuevo
from app.models.vendedor import Vendedor
from app.schemas.desarrollo_cliente import (
    DesarrolloClienteCompletarIn,
    DesarrolloClienteIn,
    DesarrolloClienteOut,
)

router = APIRouter(prefix="/desarrollo-clientes", tags=["desarrollo-clientes"])


def _a_schema(fila: DesarrolloClienteNuevo, nombre: str) -> DesarrolloClienteOut:
    return DesarrolloClienteOut(
        id=fila.id,
        vendedor_codigo=fila.vendedor_codigo,
        vendedor_nombre=nombre,
        fecha=fila.fecha,
        nombre_lugar=fila.nombre_lugar,
        zona_codigo=fila.zona_codigo,
        direccion=fila.direccion,
        fotos=fila.fotos,
        detalle_visita=fila.detalle_visita,
        completado=fila.completado,
        creado_en=fila.creado_en,
        completado_en=fila.completado_en,
    )


@router.get("", response_model=list[DesarrolloClienteOut])
async def listar_desarrollos(
    fecha: datetime.date | None = Query(default=None),
    desde: datetime.date | None = Query(default=None),
    hasta: datetime.date | None = Query(default=None),
    vendedor_codigo: str | None = Query(default=None),
    completado: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Un vendedor ve solo sus propios desarrollos de cliente nuevo.
    Supervisor/admin ven los de todos (o de uno puntual con vendedor_codigo)
    -- es la vía por la que les llega la visita ya completada, con fotos y
    detalle."""
    stmt = (
        select(DesarrolloClienteNuevo, Vendedor.nombre)
        .join(Vendedor, Vendedor.codigo_axum == DesarrolloClienteNuevo.vendedor_codigo)
    )
    if usuario.es_supervisor:
        if vendedor_codigo:
            stmt = stmt.where(DesarrolloClienteNuevo.vendedor_codigo == vendedor_codigo)
    else:
        stmt = stmt.where(DesarrolloClienteNuevo.vendedor_codigo == usuario.vendedor.codigo_axum)

    if fecha:
        stmt = stmt.where(DesarrolloClienteNuevo.fecha == fecha)
    elif desde and hasta:
        stmt = stmt.where(DesarrolloClienteNuevo.fecha.between(desde, hasta))
    if completado is not None:
        stmt = stmt.where(DesarrolloClienteNuevo.completado.is_(completado))

    stmt = stmt.order_by(DesarrolloClienteNuevo.fecha.desc(), DesarrolloClienteNuevo.creado_en.desc())
    filas = (await db.execute(stmt)).all()
    return [_a_schema(fila, nombre) for fila, nombre in filas]


@router.post("", response_model=DesarrolloClienteOut, status_code=status.HTTP_201_CREATED)
async def crear_desarrollo(
    body: DesarrolloClienteIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """A la mañana: sumar un lugar a desarrollar a la proyección del día.
    Todavía sin fotos ni detalle -- eso se carga después, al completar la
    visita."""
    fila = DesarrolloClienteNuevo(
        vendedor_codigo=usuario.vendedor.codigo_axum,
        fecha=body.fecha,
        nombre_lugar=body.nombre_lugar,
        zona_codigo=body.zona_codigo,
        direccion=body.direccion,
    )
    db.add(fila)
    await db.commit()
    await db.refresh(fila)
    return _a_schema(fila, usuario.vendedor.nombre)


@router.patch("/{desarrollo_id}/completar", response_model=DesarrolloClienteOut)
async def completar_desarrollo(
    desarrollo_id: uuid.UUID,
    body: DesarrolloClienteCompletarIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Durante el día: cargar fotos del lugar y el detalle de la visita.
    Marca la visita como completada -- recién en ese momento la ve
    supervisor/admin."""
    fila = await db.get(DesarrolloClienteNuevo, desarrollo_id)
    if fila is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Desarrollo no encontrado")
    if fila.vendedor_codigo != usuario.vendedor.codigo_axum and not usuario.es_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No es tuyo")

    fila.detalle_visita = body.detalle_visita
    fila.fotos = body.fotos
    fila.completado = True
    fila.completado_en = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    await db.refresh(fila)

    nombre = (
        await db.scalar(select(Vendedor.nombre).where(Vendedor.codigo_axum == fila.vendedor_codigo))
    ) or fila.vendedor_codigo
    return _a_schema(fila, nombre)
