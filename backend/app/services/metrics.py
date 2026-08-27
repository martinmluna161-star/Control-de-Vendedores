"""Cálculos puros de los dashboards (sin acceso a base de datos), para que
sean testeables con datos sintéticos. Los routers arman los agregados desde
SQL y le pasan los números/filas a estas funciones."""

from collections.abc import Iterable
from dataclasses import dataclass


def pct_avance_objetivo(monto_real: float, monto_objetivo: float) -> float | None:
    """% de cumplimiento del objetivo mensual. None si no hay objetivo cargado
    (evita el ZeroDivisionError y distingue "objetivo en 0" de "sin objetivo")."""
    if monto_objetivo <= 0:
        return None
    return round(float(monto_real) / float(monto_objetivo) * 100, 2)


def pct_efectividad_ruta(visitas_efectivas: int, clientes_proyectados: int) -> float | None:
    """% de clientes proyectados que efectivamente recibieron una visita."""
    if clientes_proyectados <= 0:
        return None
    return round(visitas_efectivas / clientes_proyectados * 100, 2)


@dataclass
class VentaPorFamilia:
    familia_id: int | None
    familia_desc: str | None
    monto: float


@dataclass
class CoberturaFamilia:
    familia_id: int | None
    familia_desc: str | None
    monto: float
    porcentaje: float


def cobertura_por_familia(ventas: Iterable[VentaPorFamilia]) -> list[CoberturaFamilia]:
    """Desglosa el monto vendido por familia y el % que representa cada una
    sobre el total. Ordenado de mayor a menor monto."""
    filas = list(ventas)
    total = sum(f.monto for f in filas)
    resultado = [
        CoberturaFamilia(
            familia_id=f.familia_id,
            familia_desc=f.familia_desc,
            monto=f.monto,
            porcentaje=round(f.monto / total * 100, 2) if total > 0 else 0.0,
        )
        for f in filas
    ]
    return sorted(resultado, key=lambda c: c.monto, reverse=True)


@dataclass
class MatrizFamiliaFila:
    familia_id: int | None
    familia_desc: str | None
    monto_vendido: float
    veces_proyectada: int


def matriz_cobertura_familia(
    ventas_por_familia: dict[int | None, float],
    proyecciones_por_familia: dict[int | None, int],
    nombres_familia: dict[int | None, str | None],
) -> list[MatrizFamiliaFila]:
    """Cruza, por familia, cuánto se vendió realmente contra cuántas veces esa
    familia fue propuesta en la proyección diaria de los vendedores."""
    ids = set(ventas_por_familia) | set(proyecciones_por_familia)
    filas = [
        MatrizFamiliaFila(
            familia_id=fid,
            familia_desc=nombres_familia.get(fid),
            monto_vendido=ventas_por_familia.get(fid, 0.0),
            veces_proyectada=proyecciones_por_familia.get(fid, 0),
        )
        for fid in ids
    ]
    return sorted(filas, key=lambda f: f.monto_vendido, reverse=True)


def ratio_conversion(visitas_realizadas: int, ventas_concretadas: int) -> float | None:
    """Ratio de conversión: cuántas de las visitas realizadas terminaron en
    una venta (comprobante) ese mismo día."""
    if visitas_realizadas <= 0:
        return None
    return round(ventas_concretadas / visitas_realizadas * 100, 2)


def hora_a_segundos(texto: str | None) -> int | None:
    """"HH:MM" o "HH:MM:SS" -> segundos desde medianoche. None si no se puede
    parsear (evita reventar con basura ocasional del reporte de Axum)."""
    if not texto:
        return None
    partes = texto.strip().split(":")
    try:
        numeros = [int(p) for p in partes]
    except ValueError:
        return None
    if len(numeros) == 2:
        return numeros[0] * 3600 + numeros[1] * 60
    if len(numeros) == 3:
        return numeros[0] * 3600 + numeros[1] * 60 + numeros[2]
    return None
