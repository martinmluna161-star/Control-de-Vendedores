from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, get_usuario_actual
from app.database import get_db
from app.models.cliente import Cliente
from app.models.venta import VentaDetalle
from app.models.visita import VisitaReal
from app.models.zona import Zona
from app.schemas.cliente import ClienteOut, ClienteProyeccionOut

router = APIRouter(prefix="/clientes", tags=["clientes"])


async def _verificar_acceso_zona(db: AsyncSession, usuario: UsuarioActual, zona_codigo: str) -> None:
    if usuario.es_supervisor:
        return
    zona = (await db.execute(select(Zona).where(Zona.codigo == zona_codigo))).scalar_one_or_none()
    if zona is None or zona.vendedor_codigo != usuario.vendedor.codigo_axum:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Esta zona no te pertenece")


@router.get("/por-zona/{zona_codigo}", response_model=list[ClienteProyeccionOut])
async def clientes_por_zona(
    zona_codigo: str,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Clientes de una zona, enriquecidos con última visita y venta promedio
    por visita — para la pantalla de Proyección diaria del vendedor."""
    await _verificar_acceso_zona(db, usuario, zona_codigo)

    clientes = (
        (await db.execute(select(Cliente).where(Cliente.zona_codigo == zona_codigo).order_by(Cliente.razon_social)))
        .scalars()
        .all()
    )
    if not clientes:
        return []
    codigos = [c.codigo for c in clientes]

    ultima_visita_rows = await db.execute(
        select(VisitaReal.cliente_codigo, func.max(VisitaReal.fecha))
        .where(VisitaReal.cliente_codigo.in_(codigos), VisitaReal.valida.is_(True))
        .group_by(VisitaReal.cliente_codigo)
    )
    ultima_visita = dict(ultima_visita_rows.all())

    visitas_count_rows = await db.execute(
        select(VisitaReal.cliente_codigo, func.count())
        .where(VisitaReal.cliente_codigo.in_(codigos), VisitaReal.valida.is_(True))
        .group_by(VisitaReal.cliente_codigo)
    )
    visitas_count = dict(visitas_count_rows.all())

    venta_total_rows = await db.execute(
        select(VentaDetalle.cliente_codigo, func.sum(VentaDetalle.importe))
        .where(VentaDetalle.cliente_codigo.in_(codigos))
        .group_by(VentaDetalle.cliente_codigo)
    )
    venta_total = dict(venta_total_rows.all())

    out: list[ClienteProyeccionOut] = []
    for c in clientes:
        n_visitas = visitas_count.get(c.codigo, 0)
        total = float(venta_total.get(c.codigo) or 0)
        promedio = (total / n_visitas) if n_visitas else None
        out.append(
            ClienteProyeccionOut(
                codigo=c.codigo,
                razon_social=c.razon_social,
                zona_codigo=c.zona_codigo,
                localidad=c.localidad,
                ultima_visita=ultima_visita.get(c.codigo),
                venta_promedio_por_visita=promedio,
                fuera_de_zona=False,
            )
        )
    return out


class ClienteFueraDeZonaIn(BaseModel):
    codigo: str
    razon_social: str


@router.post("/fuera-de-zona", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
async def crear_o_reutilizar_cliente_fuera_de_zona(
    body: ClienteFueraDeZonaIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Si el código de cliente ya existe, lo devuelve tal cual (no le toca la
    zona). Si no existe, lo crea sin zona asignada."""
    cliente = (await db.execute(select(Cliente).where(Cliente.codigo == body.codigo))).scalar_one_or_none()
    if cliente is None:
        cliente = Cliente(codigo=body.codigo, razon_social=body.razon_social, zona_codigo=None)
        db.add(cliente)
        await db.commit()
        await db.refresh(cliente)
    return cliente
