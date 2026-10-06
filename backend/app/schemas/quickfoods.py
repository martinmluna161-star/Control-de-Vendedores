import datetime

from pydantic import BaseModel


class FamiliaCoberturaOut(BaseModel):
    familia_id: int
    nombre: str
    obj_cob_pct: float
    real_gtm_pct: float | None
    ccc_obj: int
    ccc: int
    clientes_faltan: int


class BloqueCoberturaOut(BaseModel):
    universo_gtm_total: int
    familias: list[FamiliaCoberturaOut]


class CoberturaQuickFoodsOut(BaseModel):
    anio: int
    mes: int
    # Ventana del Universo GTM Total: últimos 3 meses terminando en anio/mes.
    desde_universo: datetime.date
    hasta_universo: datetime.date
    # Ventana de CCC (clientes con compra): solo el mes anio/mes.
    desde_ccc: datetime.date
    hasta_ccc: datetime.date
    vendedor_codigo: str | None
    vendedor_nombre: str | None
    aass: BloqueCoberturaOut
    almacenes: BloqueCoberturaOut
