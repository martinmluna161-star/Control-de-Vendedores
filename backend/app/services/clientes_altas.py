from app.models.cliente_alta import SolicitudAltaCliente

# campo del modelo -> etiqueta legible para mostrar qué falta.
CAMPOS_OBLIGATORIOS = {
    "razon_social": "Razón social",
    "direccion": "Dirección",
    "zona_codigo": "Zona / vendedor",
    "condicion_iva": "Condición IVA",
    "cuit_cuil": "CUIT o CUIL",
    "ingresos_brutos_numero": "Número de Ingresos Brutos",
    "ramo": "Ramo",
    "telefono": "Teléfono",
    "email": "Email",
    "horario": "Horario",
}


def campos_faltantes(s: SolicitudAltaCliente) -> list[str]:
    """Lista en español lo que falta para dar por terminada la carga: los
    campos obligatorios vacíos, la constancia de Ingresos Brutos (siempre
    exigida) y, si es Responsable Inscripto, la constancia de inscripción
    en IVA."""
    faltantes = [etiqueta for campo, etiqueta in CAMPOS_OBLIGATORIOS.items() if not getattr(s, campo)]
    if not s.constancia_ingresos_brutos_archivo:
        faltantes.append("Constancia de Ingresos Brutos (adjunto)")
    if s.condicion_iva == "responsable_inscripto" and not s.constancia_iva_archivo:
        faltantes.append("Constancia de Inscripción en IVA (adjunto)")
    return faltantes


def esta_completo(s: SolicitudAltaCliente) -> bool:
    return not campos_faltantes(s)
