import datetime
import uuid

from pydantic import BaseModel


class NegociacionIn(BaseModel):
    cliente_codigo: str | None = None
    cliente_nombre: str | None = None
    titulo: str
    detalle: str


class NegociacionRespuestaIn(BaseModel):
    estado: str  # aprobada | rechazada
    respuesta: str
    enviar_email: bool = False
    destinatarios_email_extra: list[str] | None = None


class NegociacionOut(BaseModel):
    id: uuid.UUID
    vendedor_codigo: str
    vendedor_nombre: str | None = None
    cliente_codigo: str | None = None
    cliente_nombre: str | None = None
    titulo: str
    detalle: str
    estado: str
    respuesta_supervisor: str | None = None
    respondido_por: str | None = None
    respondido_por_nombre: str | None = None
    respondido_en: datetime.datetime | None = None
    email_enviado: bool
    visto_por_vendedor: bool
    creado_en: datetime.datetime
