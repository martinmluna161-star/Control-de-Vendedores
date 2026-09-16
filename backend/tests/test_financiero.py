import datetime

import pytest

from app.services.financiero import (
    calcular_cashflow_semanal,
    calcular_cobros,
    construir_ventas_plan_semanal,
    estado_semaforo,
    fecha_pago_compra,
    gastos_generales_semanal,
    lunes_de_semana,
    monto_plan_semanal,
    promedio_ventas_recientes,
    semanas_del_rango,
)


def test_lunes_de_semana():
    assert lunes_de_semana(datetime.date(2026, 9, 15)) == datetime.date(2026, 9, 14)  # martes -> lunes
    assert lunes_de_semana(datetime.date(2026, 9, 14)) == datetime.date(2026, 9, 14)  # ya es lunes


def test_semanas_del_rango():
    semanas = semanas_del_rango(datetime.date(2026, 9, 15), 3)
    assert semanas == [
        datetime.date(2026, 9, 14),
        datetime.date(2026, 9, 21),
        datetime.date(2026, 9, 28),
    ]


def test_monto_plan_semanal():
    # 4.3333 semanas por mes, validado en el Sheet.
    assert round(monto_plan_semanal(130_000_000), 2) == round(130_000_000 / (52 / 12), 2)


def test_gastos_generales_semanal_no_incluye_sueldos():
    # Sección 2.4: los sueldos NO se prorratean, solo el resto.
    resultado = gastos_generales_semanal(gastos_fijos_variables_mes=10_000_000, sueldos_mensual=6_000_000)
    assert round(resultado, 2) == round(4_000_000 / (52 / 12), 2)


def test_calcular_cobros_regla_70_30():
    cobro_contado, cobro_ctacte = calcular_cobros(
        ventas_semana_actual=1_000_000, ventas_semana_anterior=800_000, pct_cobro_contado=0.70
    )
    assert cobro_contado == 700_000
    assert cobro_ctacte == pytest.approx(240_000)  # 30% de la semana anterior


def test_calcular_cobros_sin_semana_anterior():
    cobro_contado, cobro_ctacte = calcular_cobros(1_000_000, None, 0.70)
    assert cobro_contado == 700_000
    assert cobro_ctacte == 0


def test_estado_semaforo():
    assert estado_semaforo(1_000_000, umbral_riesgo=5_000_000, umbral_ajustado=30_000_000) == "riesgo"
    assert estado_semaforo(10_000_000, umbral_riesgo=5_000_000, umbral_ajustado=30_000_000) == "ajustado"
    assert estado_semaforo(50_000_000, umbral_riesgo=5_000_000, umbral_ajustado=30_000_000) == "ok"


def test_fecha_pago_compra_con_plazo():
    assert fecha_pago_compra(datetime.date(2026, 9, 1), 28) == datetime.date(2026, 9, 29)


def test_fecha_pago_compra_sin_plazo_confirmado_da_none():
    assert fecha_pago_compra(datetime.date(2026, 9, 1), None) is None


def _semanas(n, desde=datetime.date(2026, 9, 14)):
    return semanas_del_rango(desde, n)


def test_cashflow_arranca_del_saldo_de_caja_no_de_cero():
    semanas = _semanas(1)
    filas = calcular_cashflow_semanal(
        semanas,
        ventas_reales_por_semana={},
        ventas_plan_semanal_monto=0,
        compras_reales_por_semana={},
        compras_plan_semanal_monto=0,
        pago_proveedores_por_semana={},
        pago_cheques_por_semana={},
        cuotas_por_semana={},
        sueldos_y_gastos_por_semana={},
        saldo_caja_inicial=50_000_000,
        credito_total=0,
        pct_cobro_contado=0.70,
        umbral_riesgo=5_000_000,
        umbral_ajustado=30_000_000,
    )
    assert filas[0].flujo_acum_bruto == 50_000_000
    assert filas[0].flujo_acum_neto == 50_000_000
    assert filas[0].estado == "ok"


def test_cashflow_usa_ventas_real_si_existe_sino_plan():
    semanas = _semanas(2)
    filas = calcular_cashflow_semanal(
        semanas,
        ventas_reales_por_semana={semanas[0]: 1_000_000},
        ventas_plan_semanal_monto=500_000,
        compras_reales_por_semana={},
        compras_plan_semanal_monto=0,
        pago_proveedores_por_semana={},
        pago_cheques_por_semana={},
        cuotas_por_semana={},
        sueldos_y_gastos_por_semana={},
        saldo_caja_inicial=0,
        credito_total=0,
        pct_cobro_contado=0.70,
        umbral_riesgo=5_000_000,
        umbral_ajustado=30_000_000,
    )
    assert filas[0].ventas_usada == 1_000_000  # real
    assert filas[1].ventas_usada == 500_000  # plan (semana 2 sin real cargado)
    # El cobro CtaCte de la semana 2 es 30% de la venta REAL de la semana 1.
    assert filas[1].cobro_ctacte == pytest.approx(300_000)


def test_credito_usado_es_ratchet_no_se_libera_solo():
    semanas = _semanas(3)
    # Semana 1: flujo muy negativo -> usa todo el crédito disponible.
    # Semana 2: flujo positivo grande -> el acumulado bruto mejora, pero el
    # crédito usado NO baja solo.
    filas = calcular_cashflow_semanal(
        semanas,
        ventas_reales_por_semana={semanas[0]: 0, semanas[1]: 100_000_000, semanas[2]: 0},
        ventas_plan_semanal_monto=0,
        compras_reales_por_semana={},
        compras_plan_semanal_monto=0,
        pago_proveedores_por_semana={semanas[0]: 20_000_000},
        pago_cheques_por_semana={},
        cuotas_por_semana={},
        sueldos_y_gastos_por_semana={},
        saldo_caja_inicial=0,
        credito_total=10_000_000,
        pct_cobro_contado=0.70,
        umbral_riesgo=5_000_000,
        umbral_ajustado=30_000_000,
    )
    assert filas[0].flujo_acum_bruto == -20_000_000
    assert filas[0].credito_usado == 10_000_000  # tope: no puede superar credito_total
    assert filas[0].flujo_acum_neto == -10_000_000

    # Semana 2: entra mucha plata, el acumulado bruto se vuelve positivo,
    # pero el crédito usado sigue en 10M (ratchet).
    assert filas[1].flujo_acum_bruto > 0
    assert filas[1].credito_usado == 10_000_000


def test_credito_usado_nunca_supera_el_total_disponible():
    semanas = _semanas(1)
    filas = calcular_cashflow_semanal(
        semanas,
        ventas_reales_por_semana={},
        ventas_plan_semanal_monto=0,
        compras_reales_por_semana={},
        compras_plan_semanal_monto=0,
        pago_proveedores_por_semana={semanas[0]: 100_000_000},
        pago_cheques_por_semana={},
        cuotas_por_semana={},
        sueldos_y_gastos_por_semana={},
        saldo_caja_inicial=0,
        credito_total=10_000_000,
        pct_cobro_contado=0.70,
        umbral_riesgo=5_000_000,
        umbral_ajustado=30_000_000,
    )
    assert filas[0].credito_usado == 10_000_000
    assert filas[0].flujo_acum_neto == -90_000_000  # ni con todo el crédito alcanza
    assert filas[0].estado == "riesgo"


def test_compras_no_suman_al_total_egresos_son_solo_informativas():
    semanas = _semanas(1)
    filas = calcular_cashflow_semanal(
        semanas,
        ventas_reales_por_semana={},
        ventas_plan_semanal_monto=0,
        compras_reales_por_semana={semanas[0]: 5_000_000},
        compras_plan_semanal_monto=0,
        pago_proveedores_por_semana={},  # el pago (no la compra) es lo que pesa en egresos
        pago_cheques_por_semana={},
        cuotas_por_semana={},
        sueldos_y_gastos_por_semana={},
        saldo_caja_inicial=0,
        credito_total=0,
        pct_cobro_contado=0.70,
        umbral_riesgo=5_000_000,
        umbral_ajustado=30_000_000,
    )
    assert filas[0].compras_usada == 5_000_000
    assert filas[0].total_egresos == 0


def test_cashflow_usa_ventas_plan_por_semana_en_vez_del_monto_fijo():
    # VentasPlanSemanal no debe quedar congelado en un único número: si se
    # pasa un override por semana (objetivo del mes, o promedio reciente),
    # ese valor gana sobre el ventas_plan_semanal_monto fijo del Cierre
    # Estructural.
    semanas = _semanas(2)
    filas = calcular_cashflow_semanal(
        semanas,
        ventas_reales_por_semana={},
        ventas_plan_semanal_monto=100_000_000,  # el "viejo" fallback, no debería usarse
        ventas_plan_por_semana={semanas[0]: 150_000_000, semanas[1]: 180_000_000},
        compras_reales_por_semana={},
        compras_plan_semanal_monto=0,
        pago_proveedores_por_semana={},
        pago_cheques_por_semana={},
        cuotas_por_semana={},
        sueldos_y_gastos_por_semana={},
        saldo_caja_inicial=0,
        credito_total=0,
        pct_cobro_contado=0.70,
        umbral_riesgo=5_000_000,
        umbral_ajustado=30_000_000,
    )
    assert filas[0].ventas_usada == 150_000_000
    assert filas[0].ventas_plan == 150_000_000
    assert filas[1].ventas_usada == 180_000_000


def test_promedio_ventas_recientes_usa_las_ultimas_n_semanas_previas():
    semanas = _semanas(6)
    reales = {semanas[0]: 100, semanas[1]: 200, semanas[2]: 300, semanas[3]: 400}
    # Semana de referencia = semanas[4]: promedio de las últimas 4 semanas previas (0-3).
    promedio = promedio_ventas_recientes(reales, semanas[4], n_semanas=4)
    assert promedio == pytest.approx((100 + 200 + 300 + 400) / 4)


def test_promedio_ventas_recientes_solo_toma_semanas_anteriores_a_la_referencia():
    semanas = _semanas(3)
    reales = {semanas[0]: 100, semanas[1]: 200, semanas[2]: 999}  # semanas[2] es posterior/igual, no cuenta
    promedio = promedio_ventas_recientes(reales, semanas[2], n_semanas=4)
    assert promedio == pytest.approx((100 + 200) / 2)


def test_promedio_ventas_recientes_none_si_no_hay_real_previo():
    semanas = _semanas(1)
    assert promedio_ventas_recientes({}, semanas[0]) is None


def test_construir_ventas_plan_semanal_prioriza_objetivo_del_mes():
    semanas = _semanas(1)
    resultado = construir_ventas_plan_semanal(
        semanas,
        objetivos_por_mes={(semanas[0].year, semanas[0].month): 433_333_33 * 3},  # cualquier monto mensual
        ventas_reales_por_semana={},
        fallback_mensual=1,
    )
    assert resultado[semanas[0]] == pytest.approx(monto_plan_semanal(433_333_33 * 3))


def test_construir_ventas_plan_semanal_cae_a_promedio_reciente_sin_objetivo():
    semanas = _semanas(5)
    reales = {semanas[0]: 100, semanas[1]: 200, semanas[2]: 300, semanas[3]: 400}
    resultado = construir_ventas_plan_semanal(
        semanas,
        objetivos_por_mes={},  # ningún mes con objetivo cargado
        ventas_reales_por_semana=reales,
        fallback_mensual=999,
    )
    assert resultado[semanas[4]] == pytest.approx((100 + 200 + 300 + 400) / 4)


def test_construir_ventas_plan_semanal_cae_al_fallback_del_cierre_sin_real_ni_objetivo():
    semanas = _semanas(1)
    resultado = construir_ventas_plan_semanal(
        semanas,
        objetivos_por_mes={},
        ventas_reales_por_semana={},
        fallback_mensual=42,
    )
    assert resultado[semanas[0]] == 42
