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
    desde: datetime.date
    hasta: datetime.date
    vendedor_codigo: str | None
    vendedor_nombre: str | None
    aass: BloqueCoberturaOut
    almacenes: BloqueCoberturaOut
