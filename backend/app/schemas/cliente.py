import datetime

from pydantic import BaseModel, ConfigDict


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    razon_social: str
    zona_codigo: str | None
    localidad: str | None


class ClienteProyeccionOut(ClienteOut):
    """Cliente enriquecido con historial, para la pantalla de proyección diaria."""

    ultima_visita: datetime.date | None = None
    venta_promedio_por_visita: float | None = None
    fuera_de_zona: bool = False
