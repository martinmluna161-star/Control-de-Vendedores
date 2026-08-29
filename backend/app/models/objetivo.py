import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ObjetivoMensual(Base):
    """Objetivo de venta de cada vendedor para un mes puntual. Se recarga
    entero cada mes (reemplaza el objetivo anterior de ese vendedor/mes)."""

    __tablename__ = "objetivos_mensuales"

    vendedor_codigo: Mapped[str] = mapped_column(
        String(10), ForeignKey("vendedores.codigo_axum"), primary_key=True
    )
    anio: Mapped[int] = mapped_column(Integer, primary_key=True)
    mes: Mapped[int] = mapped_column(Integer, primary_key=True)
    monto: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)


class ObjetivoSugerido(Base):
    """Propuesta de objetivo mensual por vendedor calculada fuera del sistema
    (ej. en base al cierre del mes anterior) e importada como referencia para
    que supervisor/admin definan el objetivo real del mes -- ``ObjetivoMensual``
    sigue siendo el único objetivo que ve el vendedor; esto es solo el insumo
    para decidirlo."""

    __tablename__ = "objetivos_sugeridos"

    vendedor_codigo: Mapped[str] = mapped_column(
        String(10), ForeignKey("vendedores.codigo_axum"), primary_key=True
    )
    anio: Mapped[int] = mapped_column(Integer, primary_key=True)
    mes: Mapped[int] = mapped_column(Integer, primary_key=True)
    objetivo_mes_anterior: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    real_mes_anterior: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    pct_cumplimiento_mes_anterior: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    piso_recuperado: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    crecimiento_aplicado_pct: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    objetivo_sugerido: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    variacion_vs_objetivo_anterior_pct: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
