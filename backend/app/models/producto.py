from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProductoFamilia(Base):
    """Catálogo de productos con su familia, tal como se baja del ERP
    (MANTENEDOR_DE_PRODUCTOS). Se usa para completar ``familia`` en
    ``ventas_detalle`` al importar el reporte diario de ventas, cruzando
    por ``codigo_articulo``. Se recarga entero cada vez que se sube una
    versión nueva del archivo (reemplaza el catálogo anterior)."""

    __tablename__ = "productos_familia"

    codigo: Mapped[str] = mapped_column(String(20), primary_key=True)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)
    familia_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    familia_desc: Mapped[str | None] = mapped_column(String(80), nullable=True)
    baja: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Peso (kg) de una unidad de venta de este producto -- viene de la
    # columna "PesoUnitario" del mismo MANTENEDOR_DE_PRODUCTOS, para poder
    # convertir unidades vendidas a kg (ventas_detalle.unidades no está en kg).
    peso_unitario: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
