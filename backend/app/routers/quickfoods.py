import calendar
import datetime
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, get_usuario_actual
from app.database import get_db
from app.models.cliente import Cliente
from app.models.vendedor import Vendedor
from app.models.venta import VentaDetalle
from app.schemas.quickfoods import BloqueCoberturaOut, CoberturaQuickFoodsOut, FamiliaCoberturaOut
from app.services.quickfoods import FAMILIAS_QUICKFOODS_IDS, calcular_cobertura, tipo_pdv

router = APIRouter(tags=["quickfoods"])


def _hace_n_meses(fecha: datetime.date, n: int) -> datetime.date:
    mes_total = fecha.month - 1 - n
    anio = fecha.year + mes_total // 12
    mes = mes_total % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return datetime.date(anio, mes, dia)


def _limites_mes(anio: int, mes: int) -> tuple[datetime.date, datetime.date]:
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    return datetime.date(anio, mes, 1), datetime.date(anio, mes, ultimo_dia)


async def _clientes_distintos(
    db: AsyncSession,
    desde: datetime.date,
    hasta: datetime.date,
    vendedor_codigo: str | None,
    por_familia: bool,
):
    """Filas distintas (cliente, ramo) o (cliente, familia_id, ramo) de
    ventas de QuickFoods en la ventana [desde, hasta]."""
    columnas = [VentaDetalle.cliente_codigo]
    if por_familia:
        columnas.append(VentaDetalle.familia_id)
    columnas.append(Cliente.ramo)

    condiciones = [
        VentaDetalle.fecha.between(desde, hasta),
        VentaDetalle.familia_id.in_(FAMILIAS_QUICKFOODS_IDS),
        VentaDetalle.cliente_codigo.is_not(None),
    ]
    if vendedor_codigo:
        condiciones.append(VentaDetalle.vendedor_codigo == vendedor_codigo)

    return (
        await db.execute(
            select(*columnas).join(Cliente, Cliente.codigo == VentaDetalle.cliente_codigo).where(*condiciones).distinct()
        )
    ).all()


@router.get("/quickfoods/cobertura", response_model=CoberturaQuickFoodsOut)
async def cobertura_quickfoods(
    anio: int = Query(default_factory=lambda: datetime.date.today().year),
    mes: int = Query(default_factory=lambda: datetime.date.today().month, ge=1, le=12),
    vendedor_codigo: str | None = Query(
        default=None, description="Solo supervisor/admin: ver la cobertura de un solo vendedor"
    ),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Cobertura de QuickFoods (AASS vs Almacenes) de un mes puntual,
    recalculada en vivo sobre las ventas ya cargadas -- se actualiza sola a
    medida que se suben las ventas diarias, sin ningún proceso aparte. El
    vendedor ve su propia cartera; supervisor/admin ven el total de la
    distribuidora o, si filtran, la de un vendedor puntual.

    CCC (clientes con compra) cuenta solo lo comprado EN el mes elegido
    (anio/mes, por default el actual). El Universo GTM Total en cambio es
    más amplio a propósito: los últimos 3 meses terminando en el mes
    elegido, para que el denominador no colapse a 0 apenas arranca un mes
    nuevo y las distintas vistas mensuales compartan una base comparable."""
    if not (vendedor_codigo and usuario.es_supervisor):
        vendedor_codigo = None if usuario.es_supervisor else usuario.vendedor.codigo_axum

    desde_mes, hasta_mes = _limites_mes(anio, mes)
    desde_universo = _hace_n_meses(desde_mes, 2)
    hasta_universo = hasta_mes

    filas_universo = await _clientes_distintos(db, desde_universo, hasta_universo, vendedor_codigo, por_familia=False)
    filas_ccc = await _clientes_distintos(db, desde_mes, hasta_mes, vendedor_codigo, por_familia=True)

    clientes_por_tipo: dict[str, set[str]] = {"aass": set(), "almacenes": set()}
    for cliente_codigo, ramo in filas_universo:
        tipo = tipo_pdv(ramo)
        if tipo is not None:
            clientes_por_tipo[tipo].add(cliente_codigo)

    compradores_por_tipo_familia: dict[str, dict[int, set[str]]] = {
        "aass": defaultdict(set),
        "almacenes": defaultdict(set),
    }
    for cliente_codigo, familia_id, ramo in filas_ccc:
        tipo = tipo_pdv(ramo)
        if tipo is not None:
            compradores_por_tipo_familia[tipo][familia_id].add(cliente_codigo)

    def _bloque(tipo: str) -> BloqueCoberturaOut:
        universo = len(clientes_por_tipo[tipo])
        compradores_por_familia = {
            familia_id: len(clientes) for familia_id, clientes in compradores_por_tipo_familia[tipo].items()
        }
        filas_cobertura = calcular_cobertura(tipo, universo, compradores_por_familia)
        return BloqueCoberturaOut(
            universo_gtm_total=universo,
            familias=[FamiliaCoberturaOut(**vars(f)) for f in filas_cobertura],
        )

    vendedor_nombre = None
    if vendedor_codigo:
        vendedor_nombre = await db.scalar(select(Vendedor.nombre).where(Vendedor.codigo_axum == vendedor_codigo))

    return CoberturaQuickFoodsOut(
        anio=anio,
        mes=mes,
        desde_universo=desde_universo,
        hasta_universo=hasta_universo,
        desde_ccc=desde_mes,
        hasta_ccc=hasta_mes,
        vendedor_codigo=vendedor_codigo,
        vendedor_nombre=vendedor_nombre,
        aass=_bloque("aass"),
        almacenes=_bloque("almacenes"),
    )
