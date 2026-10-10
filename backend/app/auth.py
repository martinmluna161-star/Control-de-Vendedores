import asyncio
import uuid
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.vendedor import Vendedor

_bearer = HTTPBearer(auto_error=False)


class UsuarioActual:
    def __init__(self, auth_id: uuid.UUID, vendedor: Vendedor):
        self.auth_id = auth_id
        self.vendedor = vendedor

    @property
    def es_supervisor(self) -> bool:
        """Visibilidad amplia (todas las zonas, todos los vendedores): la
        tienen tanto el supervisor de campo como el admin."""
        return self.vendedor.rol in ("supervisor", "admin")

    @property
    def es_admin(self) -> bool:
        """Super usuario: además de la visibilidad de supervisor, puede
        cargar datos (objetivos, ventas, recorridos) y administrar el resto."""
        return self.vendedor.rol == "admin"

    @property
    def es_cobranzas(self) -> bool:
        """Rol acotado a cobranzas + cargas de Axum (Cta Cte/ventas/visitas):
        ve la Cuenta Corriente de todos los clientes y la bandeja de Alertas
        de cobranza, igual que el supervisor, pero no tiene ninguna otra
        visibilidad de supervisor (dashboards de equipo, objetivos, Gestión,
        etc.) -- por eso es una propiedad aparte y no se suma a
        ``es_supervisor``."""
        return self.vendedor.rol == "cobranzas"


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    # Verifica los tokens de Supabase Auth contra su JWKS público — no depende
    # de ningún secreto compartido (funciona tanto con las claves de firma
    # nuevas de Supabase como con las legacy). PyJWKClient cachea las claves,
    # así que esto no pega una request de red en cada login.
    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_url, cache_keys=True)


async def _decode_supabase_jwt(token: str) -> dict:
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El servidor no tiene configurado SUPABASE_URL",
        )
    try:
        signing_key = await asyncio.to_thread(_jwks_client().get_signing_key_from_jwt, token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from exc


async def get_usuario_actual(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> UsuarioActual:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falta el token de autenticación")

    payload = await _decode_supabase_jwt(credentials.credentials)
    auth_id = uuid.UUID(payload["sub"])

    result = await db.execute(select(Vendedor).where(Vendedor.usuario_auth_id == auth_id))
    vendedor = result.scalar_one_or_none()
    if vendedor is None or not vendedor.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este usuario no tiene un vendedor asociado en el sistema",
        )

    return UsuarioActual(auth_id=auth_id, vendedor=vendedor)


async def requerir_supervisor(usuario: UsuarioActual = Depends(get_usuario_actual)) -> UsuarioActual:
    if not usuario.es_supervisor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere rol de supervisor")
    return usuario


async def requerir_admin(usuario: UsuarioActual = Depends(get_usuario_actual)) -> UsuarioActual:
    if not usuario.es_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere rol de administrador")
    return usuario


async def requerir_cargador(usuario: UsuarioActual = Depends(get_usuario_actual)) -> UsuarioActual:
    """Puede cargar los reportes de Axum (ventas, visitas, padrón de clientes
    por zona): el admin, un usuario de 'Carga de datos' (rol ``data_entry``)
    que no tiene ningún otro permiso -- ni ve dashboards ni datos de
    clientes, solo puede subir archivos -- o el rol ``cobranzas`` (carga
    estas mismas cargas además de gestionar cobranzas)."""
    if usuario.vendedor.rol not in ("admin", "data_entry", "cobranzas"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere permiso de carga de datos")
    return usuario


async def requerir_cargador_cc(usuario: UsuarioActual = Depends(get_usuario_actual)) -> UsuarioActual:
    """Cuenta Corriente es un flujo de carga que además del admin y 'Carga de
    datos' también puede operar el supervisor de campo y el rol
    ``cobranzas`` (la cobranza es parte de su seguimiento diario, a
    diferencia de las cargas de ventas/visitas que quedan reservadas a
    admin/data_entry/cobranzas sin el supervisor)."""
    if usuario.vendedor.rol not in ("admin", "data_entry", "supervisor", "cobranzas"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere permiso de carga de datos")
    return usuario


async def requerir_gestor_cobranza(usuario: UsuarioActual = Depends(get_usuario_actual)) -> UsuarioActual:
    """Bandeja de Alertas de cobranza: supervisor/admin (ya la tenían) y el
    rol ``cobranzas``, acotado a este único propósito -- a diferencia de
    ``requerir_supervisor`` no habilita ninguna otra pantalla de supervisor."""
    if not (usuario.es_supervisor or usuario.es_cobranzas):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere permiso de gestión de cobranzas")
    return usuario
