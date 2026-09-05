import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ComentarioCobranza(Base):
    """Novedad de cobranza que un vendedor deja sobre un cliente puntual con
    saldo pendiente (ej: "prometió pagar el viernes"). Genera una alerta para
    supervisor/admin en la bandeja de Alertas y dispara un mail a
    administración -- la cuenta corriente se actualiza en el ERP, así que
    esto es solo una señal rápida, no reemplaza esa gestión."""

    __tablename__ = "cobranza_comentarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_codigo: Mapped[str] = mapped_column(String(20), ForeignKey("clientes.codigo"), nullable=False)
    cliente_razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    vendedor_codigo: Mapped[str | None] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=True)
    vendedor_nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    comentario: Mapped[str] = mapped_column(Text, nullable=False)
    # Saldo mostrado en pantalla al momento del comentario (foto informativa,
    # no se recalcula después).
    monto_adeudado: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    leido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    leido_en: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    leido_por: Mapped[str | None] = mapped_column(String(120), nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
