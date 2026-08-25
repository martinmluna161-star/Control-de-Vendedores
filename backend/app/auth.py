import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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
        return self.vendedor.rol == "supervisor"


async def _decode_supabase_jwt(token: str) -> dict:
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El servidor no tiene configurado SUPABASE_JWT_SECRET",
        )
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
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
