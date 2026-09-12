from app.routers.negociaciones import EMAILS_NEGOCIACIONES_DEFAULT, construir_destinatarios_negociacion


def test_destinatarios_sin_extra_son_solo_los_fijos():
    assert construir_destinatarios_negociacion(None) == list(EMAILS_NEGOCIACIONES_DEFAULT)
    assert construir_destinatarios_negociacion([]) == list(EMAILS_NEGOCIACIONES_DEFAULT)


def test_destinatarios_suma_extra_sin_duplicar():
    extra = ["nuevo@example.com", " otro@example.com "]
    destinatarios = construir_destinatarios_negociacion(extra)
    assert destinatarios == [*EMAILS_NEGOCIACIONES_DEFAULT, "nuevo@example.com", "otro@example.com"]


def test_destinatarios_ignora_repetidos_y_vacios():
    extra = [EMAILS_NEGOCIACIONES_DEFAULT[0], "", "   ", "nuevo@example.com"]
    destinatarios = construir_destinatarios_negociacion(extra)
    assert destinatarios == [*EMAILS_NEGOCIACIONES_DEFAULT, "nuevo@example.com"]
