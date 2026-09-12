"""Arma los eventos de la Bitácora de Comunicaciones: une en un único feed,
con una forma común, todo lo que un vendedor generó -- respuestas a avisos,
novedades de cobranza, altas de clientes nuevos y negociaciones especiales
(con la resolución del supervisor, si ya la tiene)."""

from app.models.cliente_alta import SolicitudAltaCliente
from app.models.cobranza import ComentarioCobranza
from app.models.comunicado import Comunicado
from app.models.negociacion import Negociacion
from app.schemas.bitacora import BitacoraEventoOut


def evento_desde_aviso_respondido(c: Comunicado, vendedor_nombre: str | None) -> BitacoraEventoOut:
    vendedor_codigo = (c.destinatarios_codigos or [None])[0]
    return BitacoraEventoOut(
        tipo="aviso_respuesta",
        origen_id=str(c.id),
        fecha=c.respuesta_en,
        vendedor_codigo=vendedor_codigo,
        vendedor_nombre=vendedor_nombre,
        titulo=f"Respuesta a aviso: {c.titulo}",
        detalle=c.respuesta_vendedor,
        estado="cerrado" if c.cerrado else "pendiente de cierre",
    )


def evento_desde_cobranza(c: ComentarioCobranza, vendedor_nombre: str | None) -> BitacoraEventoOut:
    return BitacoraEventoOut(
        tipo="cobranza",
        origen_id=str(c.id),
        fecha=c.creado_en,
        vendedor_codigo=c.vendedor_codigo,
        vendedor_nombre=vendedor_nombre or c.vendedor_nombre,
        titulo=f"Cobranza — {c.cliente_razon_social}",
        detalle=c.comentario,
        estado="leído" if c.leido else "pendiente",
    )


def evento_desde_alta_cliente(a: SolicitudAltaCliente, vendedor_nombre: str | None) -> BitacoraEventoOut:
    return BitacoraEventoOut(
        tipo="alta_cliente",
        origen_id=str(a.id),
        fecha=a.creado_en,
        vendedor_codigo=a.creado_por,
        vendedor_nombre=vendedor_nombre,
        titulo=f"Alta de cliente — {a.razon_social}",
        detalle=a.observaciones,
        estado="completa" if a.completo else "pendiente de completar",
    )


def evento_desde_negociacion(n: Negociacion, vendedor_nombre: str | None) -> BitacoraEventoOut:
    return BitacoraEventoOut(
        tipo="negociacion",
        origen_id=str(n.id),
        fecha=n.respondido_en or n.creado_en,
        vendedor_codigo=n.vendedor_codigo,
        vendedor_nombre=vendedor_nombre,
        titulo=f"Negociación — {n.titulo}",
        detalle=n.respuesta_supervisor or n.detalle,
        estado=n.estado,
    )


def ordenar_eventos(eventos: list[BitacoraEventoOut]) -> list[BitacoraEventoOut]:
    return sorted(eventos, key=lambda e: e.fecha, reverse=True)
