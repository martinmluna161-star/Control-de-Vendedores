import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ComentarioCobranzaIn(BaseModel):
    comentario: str = Field(min_length=1, max_length=1000)
    # Saldo que el front tenía en pantalla al momento de comentar (viene de
    # /cuentas-corrientes); puramente informativo para la alerta y el mail.
    monto_adeudado: float | None = None


class ComentarioCobranzaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cliente_codigo: str
    cliente_razon_social: str
    vendedor_codigo: str | None
    vendedor_nombre: str
    comentario: str
    monto_adeudado: float | None
    leido: bool
    leido_en: datetime.datetime | None
    leido_por: str | None
    creado_en: datetime.datetime
