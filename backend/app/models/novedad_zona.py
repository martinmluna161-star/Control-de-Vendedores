import datetime
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NovedadZona(Base):
    """Cliente agregado fuera de zona por un vendedor: el supervisor la revisa
    y decide si corresponde reasignar la zona real del cliente."""

    __tablename__ = "novedades_zona"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_codigo: Mapped[str] = mapped_column(String(20), ForeignKey("clientes.codigo"), nullable=False)
    vendedor_codigo: Mapped[str] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=False)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
