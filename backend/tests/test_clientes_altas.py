from app.models.cliente_alta import SolicitudAltaCliente
from app.services.clientes_altas import campos_faltantes, esta_completo


def _alta_completa(**overrides) -> SolicitudAltaCliente:
    datos = dict(
        razon_social="Kiosco Don José",
        direccion="San Martín 123",
        zona_codigo="1",
        condicion_iva="monotributo",
        cuit_cuil="20-12345678-9",
        ingresos_brutos_numero="123456",
        ramo="Kiosco",
        telefono="2664000000",
        email="donjose@example.com",
        horario="8 a 20",
        constancia_ingresos_brutos_archivo=b"pdf-bytes",
    )
    datos.update(overrides)
    return SolicitudAltaCliente(**datos)


def test_alta_con_todos_los_datos_esta_completa():
    alta = _alta_completa()
    assert esta_completo(alta) is True
    assert campos_faltantes(alta) == []


def test_alta_sin_telefono_ni_email_queda_pendiente():
    alta = _alta_completa(telefono=None, email=None)
    assert esta_completo(alta) is False
    assert "Teléfono" in campos_faltantes(alta)
    assert "Email" in campos_faltantes(alta)


def test_alta_sin_constancia_ingresos_brutos_queda_pendiente():
    alta = _alta_completa(constancia_ingresos_brutos_archivo=None)
    assert esta_completo(alta) is False
    assert "Constancia de Ingresos Brutos (adjunto)" in campos_faltantes(alta)


def test_responsable_inscripto_exige_constancia_iva():
    alta = _alta_completa(condicion_iva="responsable_inscripto")
    assert esta_completo(alta) is False
    assert "Constancia de Inscripción en IVA (adjunto)" in campos_faltantes(alta)

    alta.constancia_iva_archivo = b"pdf-bytes"
    assert esta_completo(alta) is True


def test_monotributo_no_exige_constancia_iva():
    alta = _alta_completa(condicion_iva="monotributo")
    assert "Constancia de Inscripción en IVA (adjunto)" not in campos_faltantes(alta)
