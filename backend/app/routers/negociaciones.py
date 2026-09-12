import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, get_usuario_actual, requerir_supervisor
from app.database import get_db
from app.models.negociacion import Negociacion
from app.models.vendedor import Vendedor
from app.schemas.negociacion import NegociacionIn, NegociacionOut, NegociacionRespuestaIn
from app.services.email import enviar_email

router = APIRouter(prefix="/negociaciones", tags=["negociaciones"])

# "Administración" y Jackie Gauna, como pide el flujo de aprobación.
EMAILS_NEGOCIACIONES_DEFAULT = (
    "adm.congeladospuntanos@gmail.com",
    "jgauna.congeladospuntanos@gmail.com",
)


def construir_destinatarios_negociacion(extra: list[str] | None) -> list[str]:
    """Los destinatarios fijos de la respuesta, más los que agregue a mano
    el supervisor/admin al responder (sin duplicados, preservando el orden)."""
    destinatarios = list(EMAILS_NEGOCIACIONES_DEFAULT)
    for correo in extra or []:
        correo = correo.strip()
        if correo and correo not in destinatarios:
            destinatarios.append(correo)
    return destinatarios


async def _out(db: AsyncSession, n: Negociacion) -> NegociacionOut:
    vendedor = await db.get(Vendedor, n.vendedor_codigo)
    respondio = await db.get(Vendedor, n.respondido_por) if n.respondido_por else None
    return NegociacionOut(
        id=n.id,
        vendedor_codigo=n.vendedor_codigo,
        vendedor_nombre=vendedor.nombre if vendedor else None,
        cliente_codigo=n.cliente_codigo,
        cliente_nombre=n.cliente_nombre,
        titulo=n.titulo,
        detalle=n.detalle,
        estado=n.estado,
        respuesta_supervisor=n.respuesta_supervisor,
        respondido_por=n.respondido_por,
        respondido_por_nombre=respondio.nombre if respondio else None,
        respondido_en=n.respondido_en,
        email_enviado=n.email_enviado,
        visto_por_vendedor=n.visto_por_vendedor,
        creado_en=n.creado_en,
    )


@router.post("", response_model=NegociacionOut, status_code=status.HTTP_201_CREATED)
async def crear_negociacion(
    body: NegociacionIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """El vendedor registra una negociación especial (descuento, condición
    comercial preferencial, etc.) que necesita aprobación de supervisor/
    admin. Queda "pendiente de revisión" hasta que la respondan."""
    negociacion = Negociacion(**body.model_dump(), vendedor_codigo=usuario.vendedor.codigo_axum)
    db.add(negociacion)
    await db.commit()
    await db.refresh(negociacion)
    return await _out(db, negociacion)


@router.get("/mias", response_model=list[NegociacionOut])
async def listar_mis_negociaciones(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Las negociaciones que cargó el propio vendedor."""
    result = await db.execute(
        select(Negociacion)
        .where(Negociacion.vendedor_codigo == usuario.vendedor.codigo_axum)
        .order_by(Negociacion.creado_en.desc())
    )
    return [await _out(db, n) for n in result.scalars().all()]


@router.post("/marcar-vistas", status_code=status.HTTP_204_NO_CONTENT)
async def marcar_negociaciones_vistas(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """El vendedor entró a su pantalla de Negociaciones: apaga el aviso de
    "tenés una respuesta nueva" de todas las suyas."""
    result = await db.execute(
        select(Negociacion).where(
            Negociacion.vendedor_codigo == usuario.vendedor.codigo_axum, Negociacion.visto_por_vendedor.is_(False)
        )
    )
    for n in result.scalars().all():
        n.visto_por_vendedor = True
    await db.commit()


@router.get("", response_model=list[NegociacionOut])
async def listar_negociaciones(
    estado: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Bandeja de negociaciones para supervisor/admin, más recientes
    primero, opcionalmente filtrada por estado."""
    stmt = select(Negociacion).order_by(Negociacion.creado_en.desc())
    if estado:
        stmt = stmt.where(Negociacion.estado == estado)
    result = await db.execute(stmt)
    return [await _out(db, n) for n in result.scalars().all()]


@router.put("/{negociacion_id}/responder", response_model=NegociacionOut)
async def responder_negociacion(
    negociacion_id: uuid.UUID,
    body: NegociacionRespuestaIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Supervisor/admin aprueba o rechaza la negociación. Deja notificado al
    vendedor (la va a ver la próxima vez que liste las suyas) y, si se pide,
    manda el acuerdo por mail a administración + destinatarios extra."""
    negociacion = await db.get(Negociacion, negociacion_id)
    if negociacion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Negociación no encontrada")
    if body.estado not in ("aprobada", "rechazada"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estado inválido")

    negociacion.estado = body.estado
    negociacion.respuesta_supervisor = body.respuesta
    negociacion.respondido_por = usuario.vendedor.codigo_axum
    negociacion.respondido_en = datetime.datetime.now(datetime.timezone.utc)
    negociacion.visto_por_vendedor = False
    negociacion.destinatarios_email_extra = body.destinatarios_email_extra
    await db.commit()
    await db.refresh(negociacion)

    if body.enviar_email:
        vendedor = await db.get(Vendedor, negociacion.vendedor_codigo)
        await enviar_email(
            construir_destinatarios_negociacion(body.destinatarios_email_extra),
            asunto=f"Negociación {'aprobada' if negociacion.estado == 'aprobada' else 'rechazada'} — {negociacion.titulo}",
            cuerpo=(
                f"Vendedor: {vendedor.nombre if vendedor else negociacion.vendedor_codigo}\n"
                f"Cliente: {negociacion.cliente_nombre or negociacion.cliente_codigo or '—'}\n"
                f"Negociación: {negociacion.titulo}\n"
                f"Detalle original: {negociacion.detalle}\n\n"
                f"Resolución: {negociacion.estado.upper()}\n"
                f"Respuesta: {body.respuesta}"
            ),
        )
        negociacion.email_enviado = True
        await db.commit()
        await db.refresh(negociacion)

    return await _out(db, negociacion)
