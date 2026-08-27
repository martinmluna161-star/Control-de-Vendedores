import calendar
import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, get_usuario_actual, requerir_supervisor
from app.database import get_db
from app.models.objetivo import ObjetivoMensual
from app.models.proyeccion import ProyeccionDiaria
from app.models.vendedor import Vendedor
from app.models.venta import VentaDetalle
from app.models.visita import VisitaReal
from app.schemas.dashboard import (
    CoberturaFamiliaOut,
    EquipoResumenOut,
    MatrizFamiliaOut,
    SellerDashboardOut,
    Supervisor360Out,
    VendedorResumenOut,
)
from app.schemas.vendedor import VendedorOut
from app.services.metrics import (
    VentaPorFamilia,
    cobertura_por_familia,
    matriz_cobertura_familia,
    pct_avance_objetivo,
    pct_efectividad_ruta,
    ratio_conversion,
)

router = APIRouter(tags=["dashboard"])


def _periodo(
    anio: int, mes: int, desde: datetime.date | None = None, hasta: datetime.date | None = None
) -> tuple[datetime.date, datetime.date]:
    if desde and hasta:
        return desde, hasta
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    return datetime.date(anio, mes, 1), datetime.date(anio, mes, ultimo_dia)


async def _resumen_vendedor(
    db: AsyncSession, vendedor_codigo: str, desde: datetime.date, hasta: datetime.date, anio: int, mes: int
) -> dict:
    monto_objetivo = await db.scalar(
        select(ObjetivoMensual.monto).where(
            ObjetivoMensual.vendedor_codigo == vendedor_codigo,
            ObjetivoMensual.anio == anio,
            ObjetivoMensual.mes == mes,
        )
    )
    monto_real = await db.scalar(
        select(func.coalesce(func.sum(VentaDetalle.importe), 0)).where(
            VentaDetalle.vendedor_codigo == vendedor_codigo,
            VentaDetalle.fecha.between(desde, hasta),
        )
    )
    visitas_proyectadas, visitas_efectivas = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(VisitaReal.valida.is_(True)),
            ).where(
                VisitaReal.vendedor_codigo == vendedor_codigo,
                VisitaReal.fecha.between(desde, hasta),
            )
        )
    ).one()
    ventas_concretadas = await db.scalar(
        select(func.count(func.distinct(func.concat(VentaDetalle.cliente_codigo, "|", VentaDetalle.fecha)))).where(
            VentaDetalle.vendedor_codigo == vendedor_codigo,
            VentaDetalle.fecha.between(desde, hasta),
        )
    )

    return {
        "monto_objetivo": float(monto_objetivo) if monto_objetivo is not None else None,
        "monto_real": float(monto_real or 0),
        "visitas_proyectadas": visitas_proyectadas,
        "visitas_efectivas": visitas_efectivas,
        "ventas_concretadas": ventas_concretadas or 0,
    }


async def _cobertura_familia_vendedor(
    db: AsyncSession, vendedor_codigo: str, desde: datetime.date, hasta: datetime.date
) -> list[CoberturaFamiliaOut]:
    filas = (
        await db.execute(
            select(
                VentaDetalle.familia_id,
                func.max(VentaDetalle.familia).label("familia_desc"),
                func.sum(VentaDetalle.importe).label("monto"),
            )
            .where(VentaDetalle.vendedor_codigo == vendedor_codigo, VentaDetalle.fecha.between(desde, hasta))
            .group_by(VentaDetalle.familia_id)
        )
    ).all()
    calculado = cobertura_por_familia(
        VentaPorFamilia(familia_id=fid, familia_desc=fdesc, monto=float(monto)) for fid, fdesc, monto in filas
    )
    return [CoberturaFamiliaOut(**vars(c)) for c in calculado]


@router.get("/vendedores", response_model=list[VendedorOut])
async def listar_vendedores(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Lista de vendedores activos, para poblar el selector de dashboards
    individuales en supervisión/administración."""
    vendedores = (
        await db.execute(select(Vendedor).where(Vendedor.activo.is_(True)).order_by(Vendedor.nombre))
    ).scalars().all()
    return vendedores


@router.get("/dashboard", response_model=SellerDashboardOut)
async def dashboard_vendedor(
    anio: int = Query(default_factory=lambda: datetime.date.today().year),
    mes: int = Query(default_factory=lambda: datetime.date.today().month, ge=1, le=12),
    desde: datetime.date | None = Query(default=None, description="Si se envía junto con hasta, reemplaza el mes"),
    hasta: datetime.date | None = Query(default=None, description="Si se envía junto con desde, reemplaza el mes"),
    vendedor_codigo: str | None = Query(
        default=None, description="Solo supervisor/admin: ver el dashboard de otro vendedor"
    ),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Métricas de rendimiento personal del vendedor logueado (o, si es
    supervisor/admin, de un vendedor puntual) para un mes o un rango de días:
    avance de objetivo, efectividad de ruta y cobertura de ventas por familia."""
    if not (vendedor_codigo and usuario.es_supervisor):
        vendedor_codigo = usuario.vendedor.codigo_axum
    desde, hasta = _periodo(anio, mes, desde, hasta)

    base = await _resumen_vendedor(db, vendedor_codigo, desde, hasta, anio, mes)
    cobertura = await _cobertura_familia_vendedor(db, vendedor_codigo, desde, hasta)

    return SellerDashboardOut(
        anio=anio,
        mes=mes,
        monto_objetivo=base["monto_objetivo"],
        monto_real=base["monto_real"],
        avance_objetivo_pct=(
            pct_avance_objetivo(base["monto_real"], base["monto_objetivo"]) if base["monto_objetivo"] else None
        ),
        clientes_proyectados=base["visitas_proyectadas"],
        visitas_efectivas=base["visitas_efectivas"],
        efectividad_ruta_pct=pct_efectividad_ruta(base["visitas_efectivas"], base["visitas_proyectadas"]),
        cobertura_por_familia=cobertura,
    )


@router.get("/supervisor/dashboard-360", response_model=Supervisor360Out)
async def dashboard_360(
    anio: int = Query(default_factory=lambda: datetime.date.today().year),
    mes: int = Query(default_factory=lambda: datetime.date.today().month, ge=1, le=12),
    desde: datetime.date | None = Query(default=None, description="Si se envía junto con hasta, reemplaza el mes"),
    hasta: datetime.date | None = Query(default=None, description="Si se envía junto con desde, reemplaza el mes"),
    vendedor_codigo: str | None = Query(default=None, description="Filtrar el detalle a un solo vendedor"),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Dashboard 360 del equipo: volumen de ventas vs. objetivos, eficiencia
    por vendedor y matriz de cobertura por familia (vendido vs. propuesto).
    Acepta un mes completo o un rango de días puntual (desde/hasta), y puede
    filtrarse a un solo vendedor para ver su detalle individual."""
    desde, hasta = _periodo(anio, mes, desde, hasta)

    stmt = select(Vendedor).where(Vendedor.activo.is_(True)).order_by(Vendedor.codigo_axum)
    if vendedor_codigo:
        stmt = stmt.where(Vendedor.codigo_axum == vendedor_codigo)
    vendedores = (await db.execute(stmt)).scalars().all()

    filas: list[VendedorResumenOut] = []
    monto_objetivo_total = 0.0
    monto_real_total = 0.0
    for v in vendedores:
        base = await _resumen_vendedor(db, v.codigo_axum, desde, hasta, anio, mes)
        avance = pct_avance_objetivo(base["monto_real"], base["monto_objetivo"]) if base["monto_objetivo"] else None
        efectividad = pct_efectividad_ruta(base["visitas_efectivas"], base["visitas_proyectadas"])
        conversion = ratio_conversion(base["visitas_efectivas"], base["ventas_concretadas"])
        filas.append(
            VendedorResumenOut(
                vendedor_codigo=v.codigo_axum,
                nombre=v.nombre,
                monto_objetivo=base["monto_objetivo"],
                monto_real=base["monto_real"],
                avance_objetivo_pct=avance,
                visitas_proyectadas=base["visitas_proyectadas"],
                visitas_efectivas=base["visitas_efectivas"],
                efectividad_ruta_pct=efectividad,
                ventas_concretadas=base["ventas_concretadas"],
                ratio_conversion_pct=conversion,
            )
        )
        monto_objetivo_total += base["monto_objetivo"] or 0
        monto_real_total += base["monto_real"]

    # Matriz de cobertura por familia: vendido real vs. veces que esa familia
    # fue propuesta en la proyección diaria de los vendedores del período.
    codigos = [v.codigo_axum for v in vendedores]
    ventas_familia_rows = (
        await db.execute(
            select(VentaDetalle.familia_id, func.max(VentaDetalle.familia), func.sum(VentaDetalle.importe))
            .where(VentaDetalle.vendedor_codigo.in_(codigos), VentaDetalle.fecha.between(desde, hasta))
            .group_by(VentaDetalle.familia_id)
        )
    ).all()
    nombres_familia = {fid: fdesc for fid, fdesc, _ in ventas_familia_rows}
    ventas_por_familia = {fid: float(monto) for fid, _, monto in ventas_familia_rows}

    proyeccion_rows = (
        await db.execute(
            select(func.unnest(ProyeccionDiaria.familias_ids))
            .where(ProyeccionDiaria.vendedor_codigo.in_(codigos), ProyeccionDiaria.fecha.between(desde, hasta))
        )
    ).all()
    proyecciones_por_familia: dict[int | None, int] = {}
    for (fid,) in proyeccion_rows:
        proyecciones_por_familia[fid] = proyecciones_por_familia.get(fid, 0) + 1

    matriz = matriz_cobertura_familia(ventas_por_familia, proyecciones_por_familia, nombres_familia)

    return Supervisor360Out(
        anio=anio,
        mes=mes,
        equipo=EquipoResumenOut(
            monto_objetivo_total=monto_objetivo_total,
            monto_real_total=monto_real_total,
            avance_objetivo_pct=pct_avance_objetivo(monto_real_total, monto_objetivo_total)
            if monto_objetivo_total
            else None,
        ),
        vendedores=filas,
        matriz_familia=[MatrizFamiliaOut(**vars(m)) for m in matriz],
    )
