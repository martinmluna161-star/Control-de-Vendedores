import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente
from app.models.venta import VentaDetalle


def rango_mes_anterior(fecha_referencia: datetime.date) -> tuple[datetime.date, datetime.date]:
    """Primer y último día del mes calendario anterior a ``fecha_referencia``."""
    primer_dia_mes = fecha_referencia.replace(day=1)
    ultimo_dia_mes_anterior = primer_dia_mes - datetime.timedelta(days=1)
    primer_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)
    return primer_dia_mes_anterior, ultimo_dia_mes_anterior


async def top_clientes_zona(
    db: AsyncSession, zona_codigo: str, fecha_referencia: datetime.date, limite: int = 5
) -> list[tuple[str, str, float]]:
    """Top N clientes de una zona por lo que compraron (importe) durante el
    mes calendario anterior a ``fecha_referencia``. Devuelve (codigo,
    razon_social, monto), ordenado de mayor a menor monto."""
    desde, hasta = rango_mes_anterior(fecha_referencia)
    filas = (
        await db.execute(
            select(Cliente.codigo, Cliente.razon_social, func.sum(VentaDetalle.importe))
            .join(VentaDetalle, VentaDetalle.cliente_codigo == Cliente.codigo)
            .where(Cliente.zona_codigo == zona_codigo, VentaDetalle.fecha.between(desde, hasta))
            .group_by(Cliente.codigo, Cliente.razon_social)
            .order_by(func.sum(VentaDetalle.importe).desc())
            .limit(limite)
        )
    ).all()
    return [(codigo, razon_social, float(monto)) for codigo, razon_social, monto in filas]
