import asyncio

from app.config import settings
from app.routers.comunicados import EMAILS_COMUNICADOS_DEFAULT, construir_destinatarios_email
from app.services.email import enviar_email


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
