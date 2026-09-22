import datetime
import uuid

from sqlalchemy import ARRAY, Boolean, Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Comunicado(Base):
    """Comunicación que supervisor/admin comparte con los vendedores: una
    promoción activa, lanzamiento de producto nuevo, producto con vencimiento
    próximo (broadcast, se muestra en la proyección diaria mientras esté
    vigente), o un "aviso" puntual a UN vendedor concreto (destinatarios_codigos
    con un solo código) que además admite una respuesta del vendedor y un
    cierre explícito de supervisor/admin una vez la vio."""

    __tablename__ = "comunicados"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # promocion | lanzamiento | vencimiento | aviso
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
    # Solo aplica a tipo "aviso": supervisor/admin cierra el ida y vuelta
    # cuando ya no hace falta seguir la conversación (ver ComunicadoMensaje).
    cerrado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cerrado_en: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cerrado_por: Mapped[str | None] = mapped_column(String(120), nullable=True)


class ComunicadoMensaje(Base):
    """Un mensaje dentro del hilo de un aviso puntual: tanto el vendedor
    destinatario como el supervisor/admin que lo escribió pueden ir sumando
    mensajes, tipo chat, sobre el mismo tema -- en vez de una única
    respuesta cerrada. Mandar un mensaje reabre el aviso si estaba cerrado."""

    __tablename__ = "comunicado_mensajes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comunicado_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("comunicados.id"), nullable=False)
    autor_codigo: Mapped[str] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=False)
    texto: Mapped[str] = mapped_column(String(1000), nullable=False)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
