import datetime
import uuid

from sqlalchemy import ARRAY, Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProyeccionDiaria(Base):
    """Qué clientes planea visitar un vendedor en una fecha puntual, y con qué
    familias de producto (``productos_familia.familia_id``) planea penetrar a
    cada uno."""

    __tablename__ = "proyeccion_diaria"
    __table_args__ = (UniqueConstraint("vendedor_codigo", "fecha", "cliente_codigo", name="uq_proyeccion_dia_cliente"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendedor_codigo: Mapped[str] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=False)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    cliente_codigo: Mapped[str] = mapped_column(String(20), ForeignKey("clientes.codigo"), nullable=False)
    fuera_de_zona: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    familias_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list, server_default="{}")
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
