from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, get_usuario_actual
from app.database import get_db
from app.models.zona import Zona
from app.schemas.zona import ZonaOut

router = APIRouter(prefix="/zonas", tags=["zonas"])


@router.get("", response_model=list[ZonaOut])
async def listar_zonas(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """El supervisor ve todas las zonas; un vendedor ve solo las suyas."""
    stmt = select(Zona).order_by(Zona.codigo)
    if not usuario.es_supervisor:
        stmt = stmt.where(Zona.vendedor_codigo == usuario.vendedor.codigo_axum)
    result = await db.execute(stmt)
    return result.scalars().all()
