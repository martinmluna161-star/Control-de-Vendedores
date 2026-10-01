"""Cobertura de QuickFoods: define las 9 familias del proveedor con su
objetivo de cobertura (% Obj Cob) por tipo de PDV, y el cálculo puro de
universo/CCC/CCC objetivo/clientes faltan -- sin acceso a base de datos,
para que sea testeable con datos sintéticos (mismo patrón que
app/services/metrics.py). El router arma las filas desde SQL y le pasa los
conteos a estas funciones.

Los objetivos son fijos (confirmados por el supervisor en septiembre 2026):
si cambian, se edita esta tabla -- no hay una pantalla de administración
para esto todavía porque el supervisor pidió que arranque simple."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FamiliaQuickFoods:
    familia_id: int
    nombre: str
    obj_cob_aass_pct: float
    obj_cob_almacenes_pct: float


# "Carne in natura porcina" (CERDO, familia_id=34) no se vende ni en AASS ni
# en Almacenes según el supervisor, así que no tiene fila en este panel.
FAMILIAS_QUICKFOODS: list[FamiliaQuickFoods] = [
    FamiliaQuickFoods(familia_id=9, nombre="Hamburguesas", obj_cob_aass_pct=95.0, obj_cob_almacenes_pct=80.0),
    FamiliaQuickFoods(familia_id=3, nombre="Salchichas", obj_cob_aass_pct=95.0, obj_cob_almacenes_pct=80.0),
    FamiliaQuickFoods(
        familia_id=7, nombre="Vegetales congelados", obj_cob_aass_pct=30.0, obj_cob_almacenes_pct=10.0
    ),
    FamiliaQuickFoods(familia_id=4, nombre="Fiambres", obj_cob_aass_pct=15.0, obj_cob_almacenes_pct=25.0),
    FamiliaQuickFoods(familia_id=27, nombre="Rebozados", obj_cob_aass_pct=50.0, obj_cob_almacenes_pct=30.0),
    FamiliaQuickFoods(familia_id=5, nombre="Papas", obj_cob_aass_pct=70.0, obj_cob_almacenes_pct=30.0),
    FamiliaQuickFoods(familia_id=25, nombre="Veggies", obj_cob_aass_pct=35.0, obj_cob_almacenes_pct=6.0),
    FamiliaQuickFoods(
        familia_id=29, nombre="Frutos congelados", obj_cob_aass_pct=10.0, obj_cob_almacenes_pct=2.0
    ),
    FamiliaQuickFoods(familia_id=36, nombre="Platos listos", obj_cob_aass_pct=35.0, obj_cob_almacenes_pct=35.0),
]

FAMILIAS_QUICKFOODS_IDS: list[int] = [f.familia_id for f in FAMILIAS_QUICKFOODS]

# Tipo de PDV para este panel, derivado del Ramo del padrón de Axum. Un
# cliente con cualquier otro ramo (Kioscos, Gastronómicos, Bares, etc.) no
# entra en ninguno de los dos universos -- decisión del supervisor, no un
# olvido: este panel solo mide AASS y Almacenes.
_RAMOS_AASS = {"AUTOSERVICIOS", "SUPERMERCADOS"}
_RAMOS_ALMACENES = {"ALMACENES"}


def tipo_pdv(ramo: str | None) -> str | None:
    """"aass", "almacenes", o None si el ramo del cliente no entra en
    ninguno de los dos universos de este panel (o no tiene ramo cargado)."""
    if ramo in _RAMOS_AASS:
        return "aass"
    if ramo in _RAMOS_ALMACENES:
        return "almacenes"
    return None


@dataclass
class FilaCobertura:
    familia_id: int
    nombre: str
    obj_cob_pct: float
    real_gtm_pct: float | None
    ccc_obj: int
    ccc: int
    clientes_faltan: int


def calcular_cobertura(
    tipo: str, universo_gtm_total: int, compradores_por_familia: dict[int, int]
) -> list[FilaCobertura]:
    """Arma las filas de cobertura de un bloque (AASS o Almacenes): para
    cada familia de QuickFoods, compara cuántos clientes del universo total
    le compraron (CCC) contra el objetivo (CCC Obj = % Obj Cob del universo,
    redondeado)."""
    filas = []
    for familia in FAMILIAS_QUICKFOODS:
        obj_cob_pct = familia.obj_cob_aass_pct if tipo == "aass" else familia.obj_cob_almacenes_pct
        ccc = compradores_por_familia.get(familia.familia_id, 0)
        ccc_obj = round(obj_cob_pct / 100 * universo_gtm_total)
        filas.append(
            FilaCobertura(
                familia_id=familia.familia_id,
                nombre=familia.nombre,
                obj_cob_pct=obj_cob_pct,
                real_gtm_pct=round(ccc / universo_gtm_total * 100, 2) if universo_gtm_total else None,
                ccc_obj=ccc_obj,
                ccc=ccc,
                clientes_faltan=max(ccc_obj - ccc, 0),
            )
        )
    return filas
