import datetime
import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProyeccionDiaria(Base):
    """Qué clientes planea visitar un vendedor en una fecha puntual.

    La familia de producto con la que se piensa penetrar cada cliente ese día
    queda pendiente de sumar (falta el mapeo código de artículo -> familia).
    """

    __tablename__ = "proyeccion_diaria"
    __table_args__ = (UniqueConstraint("vendedor_codigo", "fecha", "cliente_codigo", name="uq_proyeccion_dia_cliente"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendedor_codigo: Mapped[str] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=False)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    cliente_codigo: Mapped[str] = mapped_column(String(20), ForeignKey("clientes.codigo"), nullable=False)
    fuera_de_zona: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
