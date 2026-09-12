import datetime

from pydantic import BaseModel

TIPOS_EVENTO_BITACORA = ("aviso_respuesta", "cobranza", "alta_cliente", "negociacion")


class BitacoraEventoOut(BaseModel):
    tipo: str  # aviso_respuesta | cobranza | alta_cliente | negociacion
    origen_id: str
    fecha: datetime.datetime
    vendedor_codigo: str | None = None
    vendedor_nombre: str | None = None
    titulo: str
    detalle: str | None = None
    estado: str | None = None
