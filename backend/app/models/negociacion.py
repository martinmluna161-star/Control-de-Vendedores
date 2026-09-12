import datetime
import uuid

from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

ESTADOS_NEGOCIACION = ("pendiente", "aprobada", "rechazada")


class Negociacion(Base):
    """Negociación especial que un vendedor sube para pedirle a supervisor/
    admin una aprobación o condición comercial preferencial (descuento,
    plazo de pago, etc.) para un cliente puntual. Queda "pendiente" hasta
    que supervisor/admin la aprueba o rechaza."""

    __tablename__ = "negociaciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendedor_codigo: Mapped[str] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=False)
    cliente_codigo: Mapped[str | None] = mapped_column(String(20), ForeignKey("clientes.codigo"), nullable=True)
    # Nombre a mano por si el cliente todavía no existe en el sistema (un
    # prospecto) o el vendedor no encuentra el código al cargar rápido.
    cliente_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    detalle: Mapped[str] = mapped_column(String(2000), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    respuesta_supervisor: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    respondido_por: Mapped[str | None] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=True)
    respondido_en: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_enviado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    destinatarios_email_extra: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    # False apenas supervisor/admin responde -- se vuelve a poner en True la
    # próxima vez que el vendedor lista sus negociaciones (se lo "notifica").
    visto_por_vendedor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
