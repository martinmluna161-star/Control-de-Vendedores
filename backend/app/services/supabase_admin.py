import asyncio
import json
import logging
import urllib.error
import urllib.request
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseAdminError(Exception):
    """Error al llamar a la API de administración de Supabase Auth."""


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
        "Content-Type": "application/json",
    }


def _post_sync(path: str, body: dict) -> dict:
    url = f"{settings.supabase_url.rstrip('/')}{path}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            crudo = resp.read()
            return json.loads(crudo) if crudo else {}
    except urllib.error.HTTPError as exc:
        detalle = exc.read().decode(errors="ignore")
        logger.error("Supabase Admin API %s -> %s: %s", path, exc.code, detalle)
        raise SupabaseAdminError(detalle) from exc


def _crear_usuario_sync(email: str, password: str) -> dict:
    return _post_sync("/auth/v1/admin/users", {"email": email, "password": password, "email_confirm": True})


def _enviar_reset_sync(email: str) -> None:
    _post_sync("/auth/v1/recover", {"email": email})


async def crear_usuario_auth(email: str, password: str) -> uuid.UUID:
    """Crea el login en Supabase Auth (email ya confirmado, sin mail de
    bienvenida) y devuelve su id para guardarlo en Vendedor.usuario_auth_id."""
    if not settings.supabase_service_role_key:
        raise SupabaseAdminError("El servidor no tiene configurada SUPABASE_SERVICE_ROLE_KEY")
    data = await asyncio.to_thread(_crear_usuario_sync, email, password)
    return uuid.UUID(data["id"])


async def enviar_reset_password(email: str) -> None:
    """Dispara el mail estándar de 'restablecer contraseña' de Supabase Auth."""
    if not settings.supabase_service_role_key:
        raise SupabaseAdminError("El servidor no tiene configurada SUPABASE_SERVICE_ROLE_KEY")
    await asyncio.to_thread(_enviar_reset_sync, email)
