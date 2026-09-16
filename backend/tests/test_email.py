import asyncio
import base64
import json

from app.config import settings
from app.routers.comunicados import EMAILS_COMUNICADOS_DEFAULT, construir_destinatarios_email
from app.services.email import AdjuntoEmail, enviar_email


def test_construir_destinatarios_email_agrega_defaults_siempre():
    destinatarios = construir_destinatarios_email(None)
    assert destinatarios == list(EMAILS_COMUNICADOS_DEFAULT)


def test_construir_destinatarios_email_agrega_extra_sin_duplicar():
    destinatarios = construir_destinatarios_email(
        ["otro@congeladospuntanos.com", "recepcion.congeladospuntanos@gmail.com", "  "]
    )
    assert destinatarios == [
        "recepcion.congeladospuntanos@gmail.com",
        "jgauna.congeladospuntanos@gmail.com",
        "otro@congeladospuntanos.com",
    ]


def test_enviar_email_no_hace_nada_sin_sendgrid_configurado(monkeypatch):
    monkeypatch.setattr(settings, "sendgrid_api_key", None)
    monkeypatch.setattr(settings, "email_remitente", None)
    # No debe lanzar ni intentar conectarse a ningún servidor real.
    asyncio.run(enviar_email(["destino@example.com"], "asunto", "cuerpo"))


def test_enviar_email_no_propaga_error_de_envio(monkeypatch):
    monkeypatch.setattr(settings, "sendgrid_api_key", "clave-de-prueba")
    monkeypatch.setattr(settings, "email_remitente", "bot@example.com")

    def _falla(*args, **kwargs):
        raise OSError("sin conexión")

    monkeypatch.setattr("app.services.email._enviar_sync", _falla)
    # Un mail que no sale no debe romper la acción del usuario que lo disparó.
    asyncio.run(enviar_email(["destino@example.com"], "asunto", "cuerpo"))


def test_enviar_email_incluye_adjuntos_en_el_payload_de_sendgrid(monkeypatch):
    monkeypatch.setattr(settings, "sendgrid_api_key", "clave-de-prueba")
    monkeypatch.setattr(settings, "email_remitente", "bot@example.com")

    payload_capturado = {}

    class _RespuestaFalsa:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _urlopen_falso(req, timeout=10):
        payload_capturado.update(json.loads(req.data))
        return _RespuestaFalsa()

    monkeypatch.setattr("urllib.request.urlopen", _urlopen_falso)

    adjunto = AdjuntoEmail(nombre="constancia.pdf", contenido=b"contenido-pdf", tipo="application/pdf")
    asyncio.run(enviar_email(["destino@example.com"], "asunto", "cuerpo", adjuntos=[adjunto]))

    assert "attachments" in payload_capturado
    assert len(payload_capturado["attachments"]) == 1
    enviado = payload_capturado["attachments"][0]
    assert enviado["filename"] == "constancia.pdf"
    assert enviado["type"] == "application/pdf"
    assert base64.b64decode(enviado["content"]) == b"contenido-pdf"


def test_enviar_email_sin_adjuntos_no_agrega_la_clave_attachments(monkeypatch):
    monkeypatch.setattr(settings, "sendgrid_api_key", "clave-de-prueba")
    monkeypatch.setattr(settings, "email_remitente", "bot@example.com")

    payload_capturado = {}

    class _RespuestaFalsa:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _urlopen_falso(req, timeout=10):
        payload_capturado.update(json.loads(req.data))
        return _RespuestaFalsa()

    monkeypatch.setattr("urllib.request.urlopen", _urlopen_falso)

    asyncio.run(enviar_email(["destino@example.com"], "asunto", "cuerpo"))

    assert "attachments" not in payload_capturado
