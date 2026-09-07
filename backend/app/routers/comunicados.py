import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, get_usuario_actual, requerir_supervisor
from app.database import get_db
from app.models.comunicado import Comunicado
from app.schemas.comunicado import ComunicadoIn, ComunicadoOut, ComunicadoRespuestaIn
from app.services.email import enviar_email

router = APIRouter(prefix="/comunicados", tags=["comunicados"])

EMAILS_COMUNICADOS_DEFAULT = (
    "recepcion.congeladospuntanos@gmail.com",
    "jgauna.congeladospuntanos@gmail.com",
)

_TIPO_LABEL = {
    "promocion": "Promoción",
    "lanzamiento": "Lanzamiento",
    "vencimiento": "Vencimiento próximo",
    "aviso": "Aviso",
}


def construir_destinatarios_email(extra: list[str] | None) -> list[str]:
    """Los dos destinatarios fijos de la empresa, más los que agregue a mano
    quien publica el comunicado (sin duplicados, preservando el orden)."""
    destinatarios = list(EMAILS_COMUNICADOS_DEFAULT)
    for correo in extra or []:
        correo = correo.strip()
        if correo and correo not in destinatarios:
            destinatarios.append(correo)
    return destinatarios


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
    """Comunicados dirigidos a este vendedor (sin destinatarios puntuales =
    para todos), para mostrarle en la proyección diaria: promociones/
    lanzamientos/vencimientos vigentes hoy, más avisos puntuales que todavía
    no se cerraron -- estos últimos no dependen de fecha, quedan visibles
    hasta que supervisor/admin los cierra."""
    hoy = datetime.date.today()
    es_para_todos = or_(
        Comunicado.destinatarios_codigos.is_(None),
        func.coalesce(func.array_length(Comunicado.destinatarios_codigos, 1), 0) == 0,
    )
    vigencia = or_(
        and_(
            Comunicado.tipo != "aviso",
            Comunicado.vigente_desde <= hoy,
            (Comunicado.vigente_hasta.is_(None)) | (Comunicado.vigente_hasta >= hoy),
        ),
        and_(Comunicado.tipo == "aviso", Comunicado.cerrado.is_(False)),
    )
    result = await db.execute(
        select(Comunicado)
        .where(
            Comunicado.activo.is_(True),
            vigencia,
            or_(es_para_todos, Comunicado.destinatarios_codigos.any(usuario.vendedor.codigo_axum)),
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
    if body.tipo == "aviso" and len(body.destinatarios_codigos or []) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un aviso es para un único vendedor: elegí exactamente uno",
        )
    comunicado = Comunicado(**body.model_dump(), creado_por=usuario.vendedor.codigo_axum)
    db.add(comunicado)
    await db.commit()
    await db.refresh(comunicado)

    if comunicado.enviar_email:
        vigencia = (
            f"del {comunicado.vigente_desde} al {comunicado.vigente_hasta}"
            if comunicado.vigente_hasta
            else f"desde el {comunicado.vigente_desde}"
        )
        await enviar_email(
            construir_destinatarios_email(comunicado.destinatarios_email),
            asunto=f"[{_TIPO_LABEL.get(comunicado.tipo, comunicado.tipo)}] {comunicado.titulo}",
            cuerpo=(
                f"{comunicado.titulo}\n"
                f"Vigencia: {vigencia}\n\n"
                f"{comunicado.detalle or ''}"
            ),
        )
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


@router.post("/{comunicado_id}/responder", response_model=ComunicadoOut)
async def responder_aviso(
    comunicado_id: uuid.UUID,
    body: ComunicadoRespuestaIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """El vendedor destinatario de un aviso puntual deja su respuesta (una
    sola vez): con eso el supervisor/admin ya puede revisarla y cerrarla."""
    comunicado = await db.get(Comunicado, comunicado_id)
    if comunicado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comunicado no encontrado")
    if comunicado.tipo != "aviso":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esto no es un aviso")
    if usuario.vendedor.codigo_axum not in (comunicado.destinatarios_codigos or []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este aviso no es para vos")
    if comunicado.cerrado:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este aviso ya está cerrado")

    comunicado.respuesta_vendedor = body.respuesta
    comunicado.respuesta_en = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    await db.refresh(comunicado)
    return comunicado


@router.post("/{comunicado_id}/cerrar", response_model=ComunicadoOut)
async def cerrar_aviso(
    comunicado_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Supervisor/admin da por cerrada la comunicación una vez que revisó la
    respuesta del vendedor (o decide cerrarla sin más)."""
    comunicado = await db.get(Comunicado, comunicado_id)
    if comunicado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comunicado no encontrado")
    comunicado.cerrado = True
    comunicado.cerrado_en = datetime.datetime.now(datetime.timezone.utc)
    comunicado.cerrado_por = usuario.vendedor.nombre
    await db.commit()
    await db.refresh(comunicado)
    return comunicado
