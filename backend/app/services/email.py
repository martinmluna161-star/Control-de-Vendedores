import asyncio
import json
import logging
import urllib.request

from app.config import settings

logger = logging.getLogger(__name__)

SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


def _enviar_sync(destinatarios: list[str], asunto: str, cuerpo: str) -> None:
    payload = {
        "personalizations": [{"to": [{"email": d} for d in destinatarios]}],
        "from": {"email": settings.email_remitente},
        "subject": asunto,
        "content": [{"type": "text/plain", "value": cuerpo}],
    }
    req = urllib.request.Request(
        SENDGRID_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.sendgrid_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    # SendGrid responde 202 sin cuerpo si aceptó el mail; cualquier otro
    # código levanta HTTPError (urlopen lo hace solo).
    urllib.request.urlopen(req, timeout=10)


async def enviar_email(destinatarios: list[str], asunto: str, cuerpo: str) -> None:
    """Envía un mail por la API HTTP de SendGrid en un thread aparte para no
    bloquear el loop async. Es "best effort": si no hay API key configurada
    (por ejemplo en desarrollo local) o el envío falla, se registra el error
    y se sigue -- una notificación por mail que no sale no debería tirar
    abajo la acción del usuario (guardar un comentario, publicar un
    comunicado)."""
    if not settings.email_configurado or not destinatarios:
        return
    try:
        await asyncio.to_thread(_enviar_sync, destinatarios, asunto, cuerpo)
    except Exception:
        logger.exception("No se pudo enviar el mail '%s' a %s", asunto, destinatarios)
