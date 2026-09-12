import datetime
import uuid

from sqlalchemy import ARRAY, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

ESTADOS_EJECUCION_RUTINA = ("realizada", "replanificacion", "no_realizada")


class RutinaDiariaTarea(Base):
    """Fila de la plantilla de hoja de ruta diaria del supervisor: un bloque
    horario con su actividad. Totalmente editable -- ``dias_semana`` (nombres
    en español, ej. "Martes") decide en qué días de la semana aparece en la
    ejecución de ese día."""

    __tablename__ = "rutina_diaria_tareas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bloque_horario: Mapped[str] = mapped_column(String(80), nullable=False)
    hora_inicio: Mapped[str] = mapped_column(String(5), nullable=False)  # "HH:MM"
    hora_fin: Mapped[str] = mapped_column(String(5), nullable=False)
    dias_semana: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    # Etiqueta libre tal como la arma el supervisor (ej. "L-M-V", "Martes y
    # Jueves"), solo para mostrar -- lo que decide qué día aparece es
    # dias_semana.
    tipo_dia_texto: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    actividad_principal: Mapped[str] = mapped_column(String(200), nullable=False)
    enfoque_detalle: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    entregables_kpis: Mapped[str | None] = mapped_column(String(300), nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RutinaDiariaEjecucion(Base):
    """Estado de una tarea de la rutina para un día puntual: si se realizó,
    se replanificó o no se realizó. Una fila por (tarea, fecha); se borra si
    se vuelve a "pendiente"."""

    __tablename__ = "rutina_diaria_ejecuciones"
    __table_args__ = (UniqueConstraint("tarea_id", "fecha", name="uq_rutina_tarea_fecha"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tarea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rutina_diaria_tareas.id", ondelete="CASCADE"), nullable=False
    )
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)  # realizada | replanificacion | no_realizada
    observaciones: Mapped[str | None] = mapped_column(String(500), nullable=True)
    marcado_por: Mapped[str] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=False)
    marcado_en: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
