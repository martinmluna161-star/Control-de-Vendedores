import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, get_usuario_actual, requerir_supervisor
from app.database import get_db
from app.models.comunicado import Comunicado
from app.schemas.comunicado import ComunicadoIn, ComunicadoOut

router = APIRouter(prefix="/comunicados", tags=["comunicados"])


@router.get("", response_model=list[ComunicadoOut])
async def listar_comunicados(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Todos los comunicados (vigentes o no), para administrarlos. Solo
    supervisor/admin -- el vendedor usa /comunicados/activos."""
    result = await db.execute(select(Comunicado).order_by(Comunicado.vigente_desde.desc()))
    return result.scalars().all()


@router.get("/activos", response_model=list[ComunicadoOut])
async def listar_comunicados_activos(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Comunicados vigentes hoy, para mostrarle al vendedor en la proyección
    diaria (promociones activas, lanzamientos, productos por vencer)."""
    hoy = datetime.date.today()
    result = await db.execute(
        select(Comunicado)
        .where(
            Comunicado.activo.is_(True),
            Comunicado.vigente_desde <= hoy,
            (Comunicado.vigente_hasta.is_(None)) | (Comunicado.vigente_hasta >= hoy),
        )
        .order_by(Comunicado.tipo, Comunicado.vigente_desde.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ComunicadoOut, status_code=status.HTTP_201_CREATED)
async def crear_comunicado(
    body: ComunicadoIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    comunicado = Comunicado(**body.model_dump(), creado_por=usuario.vendedor.codigo_axum)
    db.add(comunicado)
    await db.commit()
    await db.refresh(comunicado)
    return comunicado


@router.patch("/{comunicado_id}", response_model=ComunicadoOut)
async def actualizar_comunicado(
    comunicado_id: uuid.UUID,
    body: ComunicadoIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    comunicado = await db.get(Comunicado, comunicado_id)
    if comunicado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comunicado no encontrado")
    for campo, valor in body.model_dump().items():
        setattr(comunicado, campo, valor)
    await db.commit()
    await db.refresh(comunicado)
    return comunicado


@router.post("/{comunicado_id}/desactivar", response_model=ComunicadoOut)
async def desactivar_comunicado(
    comunicado_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    comunicado = await db.get(Comunicado, comunicado_id)
    if comunicado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comunicado no encontrado")
    comunicado.activo = False
    await db.commit()
    await db.refresh(comunicado)
    return comunicado
