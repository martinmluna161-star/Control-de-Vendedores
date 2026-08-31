import datetime
import uuid

from sqlalchemy import ARRAY, Boolean, Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DesarrolloClienteNuevo(Base):
    """Visita de desarrollo de un cliente potencial (todavía no es un
    ``Cliente`` en el padrón). A la mañana el vendedor solo carga el lugar
    que va a visitar; durante el día completa la visita con fotos y detalle
    -- recién ahí queda disponible para supervisor/admin."""

    __tablename__ = "desarrollo_clientes_nuevos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendedor_codigo: Mapped[str] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=False)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    nombre_lugar: Mapped[str] = mapped_column(String(200), nullable=False)
    zona_codigo: Mapped[str | None] = mapped_column(String(10), ForeignKey("zonas.codigo"), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(300), nullable=True)
    fotos: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list, server_default="{}")
    detalle_visita: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    completado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completado_en: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
