import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

TIPOS_COMUNICADO = ("promocion", "lanzamiento", "vencimiento", "aviso")


class ComunicadoIn(BaseModel):
    tipo: str = Field(pattern="^(promocion|lanzamiento|vencimiento|aviso)$")
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
    # Solo para tipo "aviso": supervisor/admin cierra la comunicación cuando
    # ya no hace falta seguir el hilo (ver ComunicadoMensaje más abajo).
    cerrado: bool
    cerrado_en: datetime.datetime | None
    cerrado_por: str | None
    # Se completan solo al listar (no vienen del modelo): tamaño del hilo de
    # mensajes de un aviso, para verlo de un vistazo en la tabla de Gestión
    # sin tener que abrir cada uno.
    mensajes_total: int = 0
    ultimo_mensaje_en: datetime.datetime | None = None


class ComunicadoMensajeIn(BaseModel):
    texto: str = Field(min_length=1, max_length=1000)


class ComunicadoMensajeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    comunicado_id: uuid.UUID
    autor_codigo: str
    autor_nombre: str | None
    # true si lo escribió el vendedor destinatario del aviso, false si lo
    # escribió supervisor/admin -- para poder alinear la burbuja del chat.
    es_vendedor: bool
    texto: str
    creado_en: datetime.datetime
