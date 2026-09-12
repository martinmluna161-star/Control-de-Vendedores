import datetime

from app.models.cliente_alta import SolicitudAltaCliente
from app.models.cobranza import ComentarioCobranza
from app.models.comunicado import Comunicado
from app.models.negociacion import Negociacion
from app.services.bitacora import (
    evento_desde_alta_cliente,
    evento_desde_aviso_respondido,
    evento_desde_cobranza,
    evento_desde_negociacion,
    ordenar_eventos,
)


def test_evento_desde_aviso_respondido():
    aviso = Comunicado(
        tipo="aviso",
        titulo="Llegar temprano el lunes",
        vigente_desde=datetime.date(2026, 9, 1),
        creado_por="1",
        destinatarios_codigos=["26"],
        respuesta_vendedor="Dale, ahí estoy",
        respuesta_en=datetime.datetime(2026, 9, 1, 10, 0, tzinfo=datetime.timezone.utc),
        cerrado=False,
    )
    evento = evento_desde_aviso_respondido(aviso, "Juan Pérez")
    assert evento.tipo == "aviso_respuesta"
    assert evento.vendedor_codigo == "26"
    assert evento.vendedor_nombre == "Juan Pérez"
    assert evento.detalle == "Dale, ahí estoy"
    assert evento.estado == "pendiente de cierre"


def test_evento_desde_cobranza_usa_nombre_vivo_si_hay():
    comentario = ComentarioCobranza(
        cliente_codigo="123",
        cliente_razon_social="Kiosco Don José",
        vendedor_codigo="26",
        vendedor_nombre="Nombre Viejo",
        comentario="Paga el viernes",
        creado_en=datetime.datetime(2026, 9, 1, tzinfo=datetime.timezone.utc),
        leido=False,
    )
    evento = evento_desde_cobranza(comentario, "Juan Pérez (nombre actual)")
    assert evento.vendedor_nombre == "Juan Pérez (nombre actual)"
    assert evento.estado == "pendiente"


def test_evento_desde_cobranza_usa_snapshot_si_no_hay_vendedor_resuelto():
    comentario = ComentarioCobranza(
        cliente_codigo="123",
        cliente_razon_social="Kiosco Don José",
        vendedor_codigo=None,
        vendedor_nombre="Nombre Snapshot",
        comentario="Paga el viernes",
        creado_en=datetime.datetime(2026, 9, 1, tzinfo=datetime.timezone.utc),
        leido=True,
    )
    evento = evento_desde_cobranza(comentario, None)
    assert evento.vendedor_nombre == "Nombre Snapshot"
    assert evento.estado == "leído"


def test_evento_desde_alta_cliente():
    alta = SolicitudAltaCliente(
        fecha=datetime.date(2026, 9, 1),
        razon_social="Almacén La Esquina",
        creado_por="26",
        creado_en=datetime.datetime(2026, 9, 1, tzinfo=datetime.timezone.utc),
        completo=False,
    )
    evento = evento_desde_alta_cliente(alta, "Juan Pérez")
    assert evento.tipo == "alta_cliente"
    assert evento.estado == "pendiente de completar"


def test_evento_desde_negociacion_usa_fecha_respuesta_si_existe():
    negociacion = Negociacion(
        vendedor_codigo="26",
        titulo="Descuento por volumen",
        detalle="Cliente pide 10% por compra grande",
        estado="aprobada",
        respuesta_supervisor="Aprobado con tope de 8%",
        respondido_en=datetime.datetime(2026, 9, 2, tzinfo=datetime.timezone.utc),
        creado_en=datetime.datetime(2026, 9, 1, tzinfo=datetime.timezone.utc),
    )
    evento = evento_desde_negociacion(negociacion, "Juan Pérez")
    assert evento.fecha == datetime.datetime(2026, 9, 2, tzinfo=datetime.timezone.utc)
    assert evento.detalle == "Aprobado con tope de 8%"
    assert evento.estado == "aprobada"


def test_evento_desde_negociacion_pendiente_usa_fecha_de_creacion_y_detalle_original():
    negociacion = Negociacion(
        vendedor_codigo="26",
        titulo="Plazo extendido",
        detalle="Cliente pide 60 días",
        estado="pendiente",
        creado_en=datetime.datetime(2026, 9, 1, tzinfo=datetime.timezone.utc),
    )
    evento = evento_desde_negociacion(negociacion, "Juan Pérez")
    assert evento.fecha == datetime.datetime(2026, 9, 1, tzinfo=datetime.timezone.utc)
    assert evento.detalle == "Cliente pide 60 días"


def test_ordenar_eventos_mas_reciente_primero():
    from app.schemas.bitacora import BitacoraEventoOut

    viejo = BitacoraEventoOut(
        tipo="cobranza", origen_id="1", fecha=datetime.datetime(2026, 1, 1), titulo="Viejo"
    )
    nuevo = BitacoraEventoOut(
        tipo="cobranza", origen_id="2", fecha=datetime.datetime(2026, 9, 1), titulo="Nuevo"
    )
    assert ordenar_eventos([viejo, nuevo]) == [nuevo, viejo]
