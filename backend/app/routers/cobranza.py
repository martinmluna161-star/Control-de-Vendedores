import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, get_usuario_actual, requerir_supervisor
from app.database import get_db
from app.models.cliente import Cliente
from app.models.cobranza import ComentarioCobranza
from app.models.zona import Zona
from app.schemas.cobranza import ComentarioCobranzaIn, ComentarioCobranzaOut
from app.services.email import enviar_email

router = APIRouter(prefix="/cobranza", tags=["cobranza"])

EMAIL_ADMINISTRACION = "adm.congeladospuntanos@gmail.com"


def _formatear_pesos(monto: float | None) -> str:
    if monto is None:
        return "sin dato"
    return f"$ {monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@router.post(
    "/clientes/{cliente_codigo}/comentarios",
    response_model=ComentarioCobranzaOut,
    status_code=status.HTTP_201_CREATED,
)
async def crear_comentario_cobranza(
    cliente_codigo: str,
    body: ComentarioCobranzaIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """El vendedor deja una novedad de cobranza sobre uno de sus clientes:
    queda en la bandeja de Alertas de supervisor/admin y dispara un mail a
    administración. Un vendedor solo puede comentar sobre clientes de su
    propia zona actual; supervisor/admin pueden comentar sobre cualquiera."""
    cliente = await db.get(Cliente, cliente_codigo)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    vendedor_actual = None
    if cliente.zona_codigo:
        zona = await db.get(Zona, cliente.zona_codigo)
        vendedor_actual = zona.vendedor_codigo if zona else None

    if not usuario.es_supervisor and vendedor_actual != usuario.vendedor.codigo_axum:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este cliente no pertenece a tu cartera actual",
        )

    comentario = ComentarioCobranza(
        cliente_codigo=cliente.codigo,
        cliente_razon_social=cliente.razon_social,
        vendedor_codigo=vendedor_actual,
        vendedor_nombre=usuario.vendedor.nombre,
        comentario=body.comentario,
        monto_adeudado=body.monto_adeudado,
    )
    db.add(comentario)
    await db.commit()
    await db.refresh(comentario)

    await enviar_email(
        [EMAIL_ADMINISTRACION],
        asunto=f"Cobranza — {comentario.vendedor_nombre} — cliente {cliente.codigo} {cliente.razon_social}",
        cuerpo=(
            f"Vendedor: {comentario.vendedor_nombre}\n"
            f"Cliente: {cliente.codigo} - {cliente.razon_social}\n"
            f"Saldo en pantalla: {_formatear_pesos(body.monto_adeudado)}\n\n"
            f"{body.comentario}"
        ),
    )
    return comentario


@router.get("/alertas", response_model=list[ComentarioCobranzaOut])
async def listar_alertas_cobranza(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Bandeja de novedades de cobranza para supervisor/admin, más recientes
    primero."""
    result = await db.execute(select(ComentarioCobranza).order_by(ComentarioCobranza.creado_en.desc()))
    return result.scalars().all()


@router.post("/alertas/{comentario_id}/marcar-leido", response_model=ComentarioCobranzaOut)
async def marcar_leido(
    comentario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    comentario = await db.get(ComentarioCobranza, comentario_id)
    if comentario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comentario no encontrado")
    comentario.leido = True
    comentario.leido_en = datetime.datetime.now(datetime.timezone.utc)
    comentario.leido_por = usuario.vendedor.nombre
    await db.commit()
    await db.refresh(comentario)
    return comentario
