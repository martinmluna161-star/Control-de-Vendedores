import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

TIPOS_COMUNICADO = ("promocion", "lanzamiento", "vencimiento")


class ComunicadoIn(BaseModel):
    tipo: str = Field(pattern="^(promocion|lanzamiento|vencimiento)$")
    titulo: str = Field(min_length=1, max_length=200)
    detalle: str | None = Field(default=None, max_length=1000)
    vigente_desde: datetime.date
    vigente_hasta: datetime.date | None = None
    # None o [] = para todos los vendedores.
    destinatarios_codigos: list[str] | None = None
    enviar_email: bool = False
    # Destinatarios de mail ADICIONALES a los fijos de la empresa (recepción
    # y administración), que siempre se incluyen cuando enviar_email=True.
    destinatarios_email: list[str] | None = None


class ComunicadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: str
    titulo: str
    detalle: str | None
    vigente_desde: datetime.date
    vigente_hasta: datetime.date | None
    activo: bool
    destinatarios_codigos: list[str] | None
    creado_por: str
    creado_en: datetime.datetime
    enviar_email: bool
    destinatarios_email: list[str] | None
