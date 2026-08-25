from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Zona(Base):
    __tablename__ = "zonas"

    codigo: Mapped[str] = mapped_column(String(10), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    vendedor_codigo: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("vendedores.codigo_axum"), nullable=True
    )
    dia_venta: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    dia_entrega: Mapped[str] = mapped_column(String(120), nullable=False, default="")
