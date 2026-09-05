import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def _enviar_sync(destinatarios: list[str], asunto: str, cuerpo: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = settings.smtp_remitente
    msg["To"] = ", ".join(destinatarios)
    msg.set_content(cuerpo)
    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


async def enviar_email(destinatarios: list[str], asunto: str, cuerpo: str) -> None:
    """Envía un mail por SMTP en un thread aparte para no bloquear el loop
    async. Es "best effort": si el servidor no tiene SMTP configurado (por
    ejemplo en desarrollo local) o el envío falla, se registra el error y se
    sigue -- una notificación por mail que no sale no debería tirar abajo la
    acción del usuario (guardar un comentario, publicar un comunicado)."""
    if not settings.smtp_configurado or not destinatarios:
        return
    try:
        await asyncio.to_thread(_enviar_sync, destinatarios, asunto, cuerpo)
    except Exception:
        logger.exception("No se pudo enviar el mail '%s' a %s", asunto, destinatarios)
