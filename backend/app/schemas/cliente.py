import datetime

from pydantic import BaseModel, ConfigDict


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    razon_social: str
    zona_codigo: str | None
    localidad: str | None


class ClienteFreezerBadgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    marca: str  # frigor | mccain | paty
    detalle_equipos: str | None
    cantidad_freezers: int


class ClienteProyeccionOut(ClienteOut):
    """Cliente enriquecido con historial, para la pantalla de proyección diaria."""

    ultima_visita: datetime.date | None = None
    venta_promedio_por_visita: float | None = None
    fuera_de_zona: bool = False
    # Para que el front resalte "sin compra hace 1 mes" (en base a esta
    # fecha) y "cliente nuevo" (en base a creado_en) sin que el backend tenga
    # que asumir la fecha "de hoy" del usuario.
    ultima_venta: datetime.date | None = None
    creado_en: datetime.datetime
    freezers: list[ClienteFreezerBadgeOut] = []


class ClienteBusquedaOut(ClienteOut):
    """Cliente enriquecido con la zona/vendedor asignado, para la búsqueda
    general de administración y supervisión."""

    vendedor_codigo: str | None = None
    vendedor_nombre: str | None = None
    ultima_visita: datetime.date | None = None
    freezers: list[ClienteFreezerBadgeOut] = []
