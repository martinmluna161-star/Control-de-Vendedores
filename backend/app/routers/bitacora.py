from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, requerir_supervisor
from app.database import get_db
from app.models.cliente_alta import SolicitudAltaCliente
from app.models.cobranza import ComentarioCobranza
from app.models.comunicado import Comunicado, ComunicadoMensaje
from app.models.negociacion import Negociacion
from app.models.vendedor import Vendedor
from app.schemas.bitacora import BitacoraEventoOut
from app.services.bitacora import (
    evento_desde_alta_cliente,
    evento_desde_cobranza,
    evento_desde_mensaje_aviso,
    evento_desde_negociacion,
    ordenar_eventos,
)

router = APIRouter(prefix="/bitacora", tags=["bitacora"])


@router.get("", response_model=list[BitacoraEventoOut])
async def listar_bitacora(
    limite: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Bitácora / historial unificado de comunicaciones: consolida todo lo
    que generaron los vendedores -- respuestas a avisos, novedades de
    cobranza, altas de clientes nuevos y negociaciones especiales (con la
    resolución del supervisor si ya la tiene) -- en un solo feed
    cronológico. Solo lectura: cada acción (marcar leído, cerrar, completar,
    responder) se sigue haciendo desde su pantalla propia."""
    nombres = dict(
        (await db.execute(select(Vendedor.codigo_axum, Vendedor.nombre))).all()
    )

    avisos = {c.id: c for c in (await db.execute(select(Comunicado).where(Comunicado.tipo == "aviso"))).scalars().all()}
    mensajes_avisos = (
        (await db.execute(select(ComunicadoMensaje).where(ComunicadoMensaje.comunicado_id.in_(avisos.keys()))))
        .scalars()
        .all()
        if avisos
        else []
    )
    cobranzas = (await db.execute(select(ComentarioCobranza))).scalars().all()
    altas = (await db.execute(select(SolicitudAltaCliente))).scalars().all()
    negociaciones = (await db.execute(select(Negociacion))).scalars().all()

    eventos_avisos = []
    for m in mensajes_avisos:
        c = avisos[m.comunicado_id]
        destinatario = (c.destinatarios_codigos or [None])[0]
        if m.autor_codigo == destinatario:
            eventos_avisos.append(evento_desde_mensaje_aviso(c, m, nombres.get(destinatario)))

    eventos = [
        *eventos_avisos,
        *(evento_desde_cobranza(c, nombres.get(c.vendedor_codigo)) for c in cobranzas),
        *(evento_desde_alta_cliente(a, nombres.get(a.creado_por)) for a in altas),
        *(evento_desde_negociacion(n, nombres.get(n.vendedor_codigo)) for n in negociaciones),
    ]
    return ordenar_eventos(eventos)[:limite]
