import datetime
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VentaDetalle(Base):
    """Línea de comprobante del reporte diario de ventas (detalle por cliente/producto).

    ``familia`` queda nula hasta sumar el mapeo código de artículo -> familia
    (pendiente, lo baja el usuario del ERP).
    """

    __tablename__ = "ventas_detalle"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    vendedor_codigo: Mapped[str] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=False)
    cliente_codigo: Mapped[str | None] = mapped_column(String(20), ForeignKey("clientes.codigo"), nullable=True)
    comprobante_tipo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    comprobante_numero: Mapped[str | None] = mapped_column(String(40), nullable=True)
    codigo_articulo: Mapped[str] = mapped_column(String(20), nullable=False)
    descripcion_articulo: Mapped[str] = mapped_column(String(200), nullable=False)
    familia: Mapped[str | None] = mapped_column(String(80), nullable=True)
    unidades: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False, default=0)
    importe: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    descuento: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VentaTotalizada(Base):
    """Resumen del período por vendedor (reporte 'Ventas totalizadas'), usado
    para contrastar contra el objetivo mensual."""

    __tablename__ = "ventas_totalizadas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendedor_codigo: Mapped[str] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=False)
    periodo_desde: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    periodo_hasta: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    neto: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    final: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    compradores: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cantidad: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False, default=0)
    comision: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    cambios: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
