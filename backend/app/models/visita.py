import datetime
import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VisitaReal(Base):
    """Una fila del recorrido diario tal como lo baja Axum (reporte_19): cubre
    tanto lo proyectado (toda fila) como lo real (``valida=True`` cuando el
    cliente fue efectivamente visitado, con horarios). ``vendedor_codigo`` se
    completa al importar resolviendo ``zona_codigo`` contra ``zonas`` en ese
    momento, para no perder la atribución histórica si el vendedor de la zona
    cambia más adelante."""

    __tablename__ = "visitas_reales"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zona_codigo: Mapped[str] = mapped_column(String(10), nullable=False)
    vendedor_codigo: Mapped[str | None] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=True)
    cliente_codigo: Mapped[str] = mapped_column(String(20), ForeignKey("clientes.codigo"), nullable=False)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    hora_min: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hora_max: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tiempo_seg: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    larga: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
