import datetime
import uuid

from sqlalchemy import ARRAY, Boolean, Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Comunicado(Base):
    """Aviso que supervisor/admin comparte con los vendedores al armar el
    proyectado: promoción activa, lanzamiento de producto nuevo o producto
    con vencimiento próximo. Se muestra en la pantalla de proyección diaria
    y se incluye en su export mientras esté vigente."""

    __tablename__ = "comunicados"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # promocion | lanzamiento | vencimiento
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    detalle: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    vigente_desde: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # None o lista vacía = para todos los vendedores; si no, solo para estos códigos.
    destinatarios_codigos: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    creado_por: Mapped[str] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=False)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Si se marcó, al crear el comunicado también se manda por mail a los
    # destinatarios fijos de la empresa más los que se agreguen acá.
    enviar_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    destinatarios_email: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
