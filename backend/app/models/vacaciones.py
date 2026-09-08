import datetime
import uuid

from sqlalchemy import ARRAY, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Cómo se originó la propuesta de un cliente en un día del plan: puede tener
# más de un origen (ej. estaba proyectado Y además compró la última vez).
ORIGENES_PROPUESTA = ("proyectado", "visita", "venta", "manual")


class VacacionesPlan(Base):
    """Plan de cobertura para el período de vacaciones de un vendedor: quién
    se va, y desde/hasta cuándo. Contiene un ``VacacionesPlanDia`` por cada
    combinación fecha+zona que ese vendedor cubre normalmente en ese rango."""

    __tablename__ = "vacaciones_planes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendedor_codigo: Mapped[str] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=False)
    fecha_desde: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    fecha_hasta: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    creado_por: Mapped[str] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=False)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VacacionesPlanDia(Base):
    """Una zona puntual que hay que cubrir en una fecha puntual del plan
    (un vendedor puede cubrir más de una zona el mismo día de la semana, así
    que la unidad de asignación es fecha+zona, no solo la fecha). El
    reemplazante se asigna acá; al asignarlo, sus clientes propuestos se
    escriben como proyección diaria REAL de ese vendedor para esa fecha."""

    __tablename__ = "vacaciones_planes_dias"
    __table_args__ = (UniqueConstraint("plan_id", "fecha", "zona_codigo", name="uq_vacaciones_dia_zona"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vacaciones_planes.id", ondelete="CASCADE"), nullable=False
    )
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    zona_codigo: Mapped[str] = mapped_column(String(10), ForeignKey("zonas.codigo"), nullable=False)
    vendedor_reemplazo_codigo: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("vendedores.codigo_axum"), nullable=True
    )
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VacacionesPlanCliente(Base):
    """Cliente propuesto (o agregado a mano) para un día+zona del plan, con
    las familias/observaciones que se le van a escribir a la proyección del
    reemplazante. ``origenes`` guarda de dónde salió la propuesta, para que
    el front lo muestre y quien arma el plan priorice con criterio."""

    __tablename__ = "vacaciones_planes_clientes"
    __table_args__ = (UniqueConstraint("plan_dia_id", "cliente_codigo", name="uq_vacaciones_dia_cliente"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_dia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vacaciones_planes_dias.id", ondelete="CASCADE"), nullable=False
    )
    cliente_codigo: Mapped[str] = mapped_column(String(20), ForeignKey("clientes.codigo"), nullable=False)
    origenes: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    familias_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    observaciones: Mapped[str | None] = mapped_column(String(500), nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
