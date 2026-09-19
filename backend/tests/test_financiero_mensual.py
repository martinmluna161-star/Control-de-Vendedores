import pytest

from app.services.financiero_mensual import (
    calcular_cobertura,
    calcular_estado_resultados_mes,
    calcular_proyeccion_escenario,
    calcular_venta_equilibrio,
    etiqueta_mes,
    mes_siguiente,
    meses_del_rango,
    tramo_antiguedad,
)


def test_etiqueta_mes():
    assert etiqueta_mes(2026, 8) == "Ago-26"
    assert etiqueta_mes(2027, 1) == "Ene-27"


def test_mes_siguiente_cruza_anio():
    assert mes_siguiente(2026, 12) == (2027, 1)
    assert mes_siguiente(2026, 8) == (2026, 9)


def test_meses_del_rango():
    assert meses_del_rango(2026, 11, 4) == [(2026, 11), (2026, 12), (2027, 1), (2027, 2)]


def test_tramo_antiguedad():
    assert tramo_antiguedad(0) == "Al día"
    assert tramo_antiguedad(-3) == "Al día"  # todavía no vence
    assert tramo_antiguedad(15) == "1 a 15 días"
    assert tramo_antiguedad(30) == "16 a 30 días"
    assert tramo_antiguedad(60) == "31 a 60 días"
    assert tramo_antiguedad(90) == "61 a 90 días"
    assert tramo_antiguedad(91) == "Más de 90 días"


# Los siguientes números son los reales de Ago-26 del tablero de referencia
# (congeladospuntanosdashboard.vercel.app) -- validan que el motor reproduce
# el mismo resultado con la misma lógica.


def test_estado_resultados_mes_reproduce_ago26_del_tablero_referencia():
    r = calcular_estado_resultados_mes(
        anio=2026,
        mes=8,
        ventas=670_000_000,
        costo_mercaderia=-501_000_000,
        gastos_variables=-27_400_000,
        gastos_fijos=-9_300_000,
        sueldos_y_cargas=-67_000_000,
        casilla=-4_800_000,
        ingresos_brutos=-15_900_000,
        retiros_socios=-15_300_000,
        iva=-2_800_000,
        intereses=-45_800_000,
        alicuota_ganancias=0.35,
    )
    assert r.margen_bruto == 169_000_000
    assert round(r.margen_bruto_pct * 100, 1) == 25.2
    assert r.ebitda == 26_500_000
    assert r.resultado_neto == pytest.approx(-19_300_000, abs=100_000)


def test_estado_resultados_mes_sin_ventas_no_rompe():
    r = calcular_estado_resultados_mes(anio=2026, mes=1, ventas=0, costo_mercaderia=0)
    assert r.margen_bruto_pct is None
    assert r.ebitda_pct is None


def test_estado_resultados_mes_no_genera_impuesto_a_perdida():
    r = calcular_estado_resultados_mes(
        anio=2026, mes=1, ventas=100, costo_mercaderia=-90, gastos_fijos=-50, alicuota_ganancias=0.35
    )
    assert r.antes_ganancias < 0
    assert r.impuesto_ganancias == 0  # nunca se "gana" impuesto sobre pérdida


def test_venta_equilibrio_reproduce_ago26_del_tablero_referencia():
    eq = calcular_venta_equilibrio(
        ventas=670_000_000,
        costo_mercaderia=-501_000_000,
        gastos_variables=-27_400_000,
        gastos_fijos=-9_300_000,
        sueldos_y_cargas=-67_000_000,
        casilla=-4_800_000,
        ingresos_brutos=-15_900_000,
        iva=-2_800_000,
        intereses=-45_800_000,
        retiros_socios=-15_300_000,
    )
    assert round(eq["margen_contribucion_pct"] * 100, 1) == 21.1
    assert eq["costos_fijos_totales"] == 145_600_000
    assert eq["venta_equilibrio"] == pytest.approx(689_063_888, rel=0.001)
    assert eq["venta_equilibrio_con_retiros"] == pytest.approx(761_479_214, rel=0.001)


def test_venta_equilibrio_sin_ventas_no_rompe():
    eq = calcular_venta_equilibrio(
        ventas=0, costo_mercaderia=0, gastos_variables=0, gastos_fijos=-10, sueldos_y_cargas=0,
        casilla=0, ingresos_brutos=0, iva=0, intereses=0,
    )
    assert eq["margen_contribucion_pct"] is None
    assert eq["venta_equilibrio"] is None


def test_proyeccion_escenario_ebitda_y_cobertura_reproduce_base_del_tablero_referencia():
    # Escenario Base del tablero de referencia, con el cronograma real
    # (sueldos/casilla/IIBB/IVA/cuota/intereses/capital) mes a mes, Sep-26 a
    # Jun-27: EBITDA total $395.043.416, cobertura 0,58x.
    meses = meses_del_rango(2026, 9, 10)
    cronograma = {
        (2026, 9): (-68_358_387, -4_875_530, 85_240_709, 35_226_588, 50_014_121),
        (2026, 10): (-69_725_555, -4_973_041, 84_847_362, 34_911_425, 49_935_937),
        (2026, 11): (-71_120_066, -5_072_502, 83_515_730, 33_601_055, 49_914_675),
        (2026, 12): (-98_632_390, -5_173_952, 69_285_844, 27_929_480, 41_356_364),
        (2027, 1): (-73_993_317, -5_277_431, 64_600_944, 24_810_979, 39_789_965),
        (2027, 2): (-75_473_183, -5_382_980, 61_346_501, 24_363_622, 36_982_879),
        (2027, 3): (-76_982_647, -5_490_639, 58_795_668, 23_458_010, 35_337_658),
        (2027, 4): (-78_522_300, -5_600_452, 58_271_775, 22_954_976, 35_316_799),
        (2027, 5): (-80_092_746, -5_712_461, 56_622_562, 22_465_758, 34_156_804),
        (2027, 6): (-111_076_001, -5_826_710, 55_831_290, 21_690_017, 34_141_273),
    }
    fijos_por_mes = {
        m: {"sueldos_y_cargas": sueldos, "casilla": casilla, "ingresos_brutos": -15_855_119, "iva": -2_768_843}
        for m, (sueldos, casilla, _, _, _) in cronograma.items()
    }
    cuota_por_mes = {m: v[2] for m, v in cronograma.items()}
    intereses_por_mes = {m: v[3] for m, v in cronograma.items()}
    capital_por_mes = {m: v[4] for m, v in cronograma.items()}

    filas = calcular_proyeccion_escenario(
        meses,
        ventas_mes_base=670_000_000,
        saldo_caja_inicial=-115_796_539,
        crecimiento_ventas_mensual=0.02,
        margen_bruto=0.27,
        inflacion_gastos_mensual=0.02,
        alicuota_ganancias=0.35,
        retiros_pct_ventas=0.0228358,
        gastos_variables_base=27_400_000,
        gastos_fijos_base=9_300_000,
        fijos_por_mes=fijos_por_mes,
        cuota_deuda_por_mes=cuota_por_mes,
        intereses_por_mes=intereses_por_mes,
        capital_por_mes=capital_por_mes,
    )
    assert len(filas) == 10
    assert filas[0].anio == 2026 and filas[0].mes == 9
    assert filas[0].ventas == pytest.approx(683_400_000, rel=0.001)
    assert filas[0].ebitda == pytest.approx(39_528_604, rel=0.01)

    cobertura = calcular_cobertura(filas)
    assert cobertura["ebitda_total"] == pytest.approx(395_043_416, rel=0.01)
    assert cobertura["cobertura"] == pytest.approx(0.582, abs=0.01)
    assert cobertura["deficit"] > 0


def test_proyeccion_escenario_banco_es_un_acumulado_recursivo():
    meses = meses_del_rango(2026, 9, 2)
    filas = calcular_proyeccion_escenario(
        meses,
        ventas_mes_base=100_000_000,
        saldo_caja_inicial=-10_000_000,
        crecimiento_ventas_mensual=0.0,
        margen_bruto=0.30,
        inflacion_gastos_mensual=0.0,
        alicuota_ganancias=0.35,
        retiros_pct_ventas=0.0,
        gastos_variables_base=0,
        gastos_fijos_base=0,
        fijos_por_mes={},
        cuota_deuda_por_mes={},
        intereses_por_mes={},
        capital_por_mes={},
    )
    # Sin deuda ni gastos fijos cargados: EBITDA = margen bruto entero, y
    # como no hay intereses que lo compensen, paga ganancias sobre el total.
    assert filas[0].ebitda == pytest.approx(30_000_000)
    impuesto_esperado = -0.35 * 30_000_000
    assert filas[0].banco_acumulado == pytest.approx(-10_000_000 + 30_000_000 + impuesto_esperado)
    assert filas[1].banco_acumulado == pytest.approx(filas[0].banco_acumulado + 30_000_000 + impuesto_esperado)
