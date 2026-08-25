from sqlalchemy import ForeignKey, Integer, Numeric, String
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
