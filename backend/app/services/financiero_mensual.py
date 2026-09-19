"""Motor del tablero financiero MENSUAL (Estado de Resultados, punto de
equilibrio, deuda, cobranzas y proyección a 10 meses por escenario) --
cálculo puro, sin DB, testeable. Es un modelo complementario al cashflow
SEMANAL ya existente (app/services/financiero.py): éste responde "¿la
empresa gana o pierde plata, y aguanta la deuda?", aquél "¿me alcanza la
plata esta semana?". El router junta los datos de origen y les pasa
listas/dicts a estas funciones.

Convención de signos: todo lo que sale de la empresa (costos, gastos,
retiros, intereses, impuestos) se pasa y se devuelve en NEGATIVO. Ventas y
resultados positivos, en positivo."""

import dataclasses
import datetime

MESES_ABREV = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def etiqueta_mes(anio: int, mes: int) -> str:
    return f"{MESES_ABREV[mes - 1]}-{str(anio)[2:]}"


def mes_siguiente(anio: int, mes: int) -> tuple[int, int]:
    return (anio + 1, 1) if mes == 12 else (anio, mes + 1)


def meses_del_rango(anio_desde: int, mes_desde: int, cantidad: int) -> list[tuple[int, int]]:
    meses = []
    anio, mes = anio_desde, mes_desde
    for _ in range(cantidad):
        meses.append((anio, mes))
        anio, mes = mes_siguiente(anio, mes)
    return meses


@dataclasses.dataclass
class EstadoResultadosMes:
    anio: int
    mes: int
    ventas: float
    costo_mercaderia: float
    margen_bruto: float
    margen_bruto_pct: float | None
    gastos_variables: float
    gastos_fijos: float
    sueldos_y_cargas: float
    casilla: float
    ingresos_brutos: float
    retiros_socios: float
    iva: float
    gastos_operativos: float
    ebitda: float
    ebitda_pct: float | None
    intereses: float
    antes_ganancias: float
    impuesto_ganancias: float
    resultado_neto: float


def calcular_estado_resultados_mes(
    *,
    anio: int,
    mes: int,
    ventas: float,
    costo_mercaderia: float,
    gastos_variables: float = 0.0,
    gastos_fijos: float = 0.0,
    sueldos_y_cargas: float = 0.0,
    casilla: float = 0.0,
    ingresos_brutos: float = 0.0,
    retiros_socios: float = 0.0,
    iva: float = 0.0,
    intereses: float = 0.0,
    alicuota_ganancias: float = 0.35,
) -> EstadoResultadosMes:
    """EBITDA = margen bruto + gastos operativos. El impuesto a las
    ganancias solo se calcula sobre resultado positivo después de intereses
    (nunca se "gana" un impuesto negativo)."""
    margen_bruto = ventas + costo_mercaderia
    margen_bruto_pct = (margen_bruto / ventas) if ventas else None
    gastos_operativos = (
        gastos_variables + gastos_fijos + sueldos_y_cargas + casilla + ingresos_brutos + retiros_socios + iva
    )
    ebitda = margen_bruto + gastos_operativos
    ebitda_pct = (ebitda / ventas) if ventas else None
    antes_ganancias = ebitda + intereses
    impuesto_ganancias = -alicuota_ganancias * max(0.0, antes_ganancias)
    resultado_neto = antes_ganancias + impuesto_ganancias
    return EstadoResultadosMes(
        anio=anio,
        mes=mes,
        ventas=ventas,
        costo_mercaderia=costo_mercaderia,
        margen_bruto=margen_bruto,
        margen_bruto_pct=margen_bruto_pct,
        gastos_variables=gastos_variables,
        gastos_fijos=gastos_fijos,
        sueldos_y_cargas=sueldos_y_cargas,
        casilla=casilla,
        ingresos_brutos=ingresos_brutos,
        retiros_socios=retiros_socios,
        iva=iva,
        gastos_operativos=gastos_operativos,
        ebitda=ebitda,
        ebitda_pct=ebitda_pct,
        intereses=intereses,
        antes_ganancias=antes_ganancias,
        impuesto_ganancias=impuesto_ganancias,
        resultado_neto=resultado_neto,
    )


def calcular_venta_equilibrio(
    *,
    ventas: float,
    costo_mercaderia: float,
    gastos_variables: float,
    gastos_fijos: float,
    sueldos_y_cargas: float,
    casilla: float,
    ingresos_brutos: float,
    iva: float,
    intereses: float,
    retiros_socios: float = 0.0,
) -> dict:
    """"Cuánto hay que vender": margen de contribución sobre costos
    variables, contra los costos que se pagan siempre (fijos + sueldos +
    casilla + IIBB + IVA + intereses), sin importar cuánto se venda."""
    margen_contribucion_pct = (ventas + costo_mercaderia + gastos_variables) / ventas if ventas else None
    costos_fijos_totales = -(gastos_fijos + sueldos_y_cargas + casilla + ingresos_brutos + iva + intereses)
    venta_equilibrio = (costos_fijos_totales / margen_contribucion_pct) if margen_contribucion_pct else None
    pct_de_la_venta = (venta_equilibrio / ventas) if (venta_equilibrio is not None and ventas) else None
    faltante = (venta_equilibrio - ventas) if venta_equilibrio is not None else None
    venta_equilibrio_con_retiros = (
        ((costos_fijos_totales - retiros_socios) / margen_contribucion_pct) if margen_contribucion_pct else None
    )
    return {
        "margen_contribucion_pct": margen_contribucion_pct,
        "costos_fijos_totales": costos_fijos_totales,
        "venta_equilibrio": venta_equilibrio,
        "pct_de_la_venta": pct_de_la_venta,
        "faltante": faltante,
        "venta_equilibrio_con_retiros": venta_equilibrio_con_retiros,
    }


TRAMOS_ANTIGUEDAD = ("Al día", "1 a 15 días", "16 a 30 días", "31 a 60 días", "61 a 90 días", "Más de 90 días")


def tramo_antiguedad(dias_vencido: int) -> str:
    if dias_vencido <= 0:
        return "Al día"
    if dias_vencido <= 15:
        return "1 a 15 días"
    if dias_vencido <= 30:
        return "16 a 30 días"
    if dias_vencido <= 60:
        return "31 a 60 días"
    if dias_vencido <= 90:
        return "61 a 90 días"
    return "Más de 90 días"


@dataclasses.dataclass
class FilaProyeccionMes:
    anio: int
    mes: int
    ventas: float
    costo_mercaderia: float
    margen_bruto: float
    margen_bruto_pct: float
    gastos_variables: float
    gastos_fijos: float
    sueldos_y_cargas: float
    retiros_socios: float
    casilla: float
    ingresos_brutos: float
    iva: float
    gastos_operativos: float
    ebitda: float
    ebitda_pct: float
    cuota_deuda: float
    intereses_pagados: float
    capital_amortizado: float
    resultado_despues_deuda: float
    antes_ganancias: float
    impuesto_ganancias: float
    resultado_neto: float
    banco_acumulado: float


def calcular_proyeccion_escenario(
    meses: list[tuple[int, int]],
    *,
    ventas_mes_base: float,
    saldo_caja_inicial: float,
    crecimiento_ventas_mensual: float,
    margen_bruto: float,
    inflacion_gastos_mensual: float,
    alicuota_ganancias: float,
    retiros_pct_ventas: float,
    gastos_variables_base: float,
    gastos_fijos_base: float,
    fijos_por_mes: dict[tuple[int, int], dict],
    cuota_deuda_por_mes: dict[tuple[int, int], float],
    intereses_por_mes: dict[tuple[int, int], float],
    capital_por_mes: dict[tuple[int, int], float],
) -> list[FilaProyeccionMes]:
    """Sección "Proyección": ventas crecen geométricamente, gastos
    variables/fijos se inflacionan mes a mes; todo lo que viene de un
    cronograma real (sueldos, casilla, IIBB, IVA, cuota, intereses, capital)
    NO se proyecta -- es igual en los 4 escenarios, sale de lo cargado."""
    filas: list[FilaProyeccionMes] = []
    ventas_prev = ventas_mes_base
    banco_prev = saldo_caja_inicial
    for i, (anio, mes) in enumerate(meses, start=1):
        ventas = ventas_prev * (1 + crecimiento_ventas_mensual)
        costo_mercaderia = -ventas * (1 - margen_bruto)
        margen_bruto_pesos = ventas + costo_mercaderia
        margen_bruto_pct = (margen_bruto_pesos / ventas) if ventas else 0.0

        gastos_variables = -abs(gastos_variables_base) * ((1 + inflacion_gastos_mensual) ** i)
        gastos_fijos = -abs(gastos_fijos_base) * ((1 + inflacion_gastos_mensual) ** i)
        retiros_socios = -retiros_pct_ventas * ventas

        fijo = fijos_por_mes.get((anio, mes), {})
        sueldos_y_cargas = fijo.get("sueldos_y_cargas", 0.0)
        casilla = fijo.get("casilla", 0.0)
        ingresos_brutos = fijo.get("ingresos_brutos", 0.0)
        iva = fijo.get("iva", 0.0)

        gastos_operativos = (
            gastos_variables + gastos_fijos + sueldos_y_cargas + retiros_socios + casilla + ingresos_brutos + iva
        )
        ebitda = margen_bruto_pesos + gastos_operativos
        ebitda_pct = (ebitda / ventas) if ventas else 0.0

        cuota_deuda = cuota_deuda_por_mes.get((anio, mes), 0.0)
        intereses_pagados = -abs(intereses_por_mes.get((anio, mes), 0.0))
        capital_amortizado = capital_por_mes.get((anio, mes), 0.0)

        resultado_despues_deuda = ebitda - cuota_deuda
        antes_ganancias = ebitda + intereses_pagados
        impuesto_ganancias = -alicuota_ganancias * max(0.0, antes_ganancias)
        resultado_neto = antes_ganancias + impuesto_ganancias

        banco_acumulado = banco_prev + resultado_despues_deuda + impuesto_ganancias

        filas.append(
            FilaProyeccionMes(
                anio=anio,
                mes=mes,
                ventas=ventas,
                costo_mercaderia=costo_mercaderia,
                margen_bruto=margen_bruto_pesos,
                margen_bruto_pct=margen_bruto_pct,
                gastos_variables=gastos_variables,
                gastos_fijos=gastos_fijos,
                sueldos_y_cargas=sueldos_y_cargas,
                retiros_socios=retiros_socios,
                casilla=casilla,
                ingresos_brutos=ingresos_brutos,
                iva=iva,
                gastos_operativos=gastos_operativos,
                ebitda=ebitda,
                ebitda_pct=ebitda_pct,
                cuota_deuda=cuota_deuda,
                intereses_pagados=intereses_pagados,
                capital_amortizado=capital_amortizado,
                resultado_despues_deuda=resultado_despues_deuda,
                antes_ganancias=antes_ganancias,
                impuesto_ganancias=impuesto_ganancias,
                resultado_neto=resultado_neto,
                banco_acumulado=banco_acumulado,
            )
        )
        ventas_prev = ventas
        banco_prev = banco_acumulado
    return filas


def calcular_cobertura(filas: list[FilaProyeccionMes]) -> dict:
    ebitda_total = sum(f.ebitda for f in filas)
    servicio_deuda_total = sum(f.cuota_deuda for f in filas)
    cobertura = (ebitda_total / servicio_deuda_total) if servicio_deuda_total else None
    return {
        "ebitda_total": ebitda_total,
        "servicio_deuda_total": servicio_deuda_total,
        "cobertura": cobertura,
        "deficit": (servicio_deuda_total - ebitda_total) if servicio_deuda_total > ebitda_total else 0.0,
    }
