import datetime
import uuid

from pydantic import BaseModel


class SolicitudAltaClienteOut(BaseModel):
    id: uuid.UUID
    fecha: datetime.date
    razon_social: str
    direccion: str | None = None
    zona_codigo: str | None = None
    condicion_iva: str | None = None
    cuit_cuil: str | None = None
    ingresos_brutos_numero: str | None = None
    ramo: str | None = None
    telefono: str | None = None
    email: str | None = None
    horario: str | None = None
    observaciones: str | None = None
    tiene_constancia_iva: bool = False
    constancia_iva_nombre: str | None = None
    tiene_constancia_ingresos_brutos: bool = False
    constancia_ingresos_brutos_nombre: str | None = None
    completo: bool
    completado_en: datetime.datetime | None = None
    creado_por: str
    creado_en: datetime.datetime
    faltantes: list[str] = []
