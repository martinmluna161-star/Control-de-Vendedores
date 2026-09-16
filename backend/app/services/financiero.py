"""Motor de proyección semanal de cashflow -- migración de la lógica
validada en el Google Sheet de Congelados Puntanos. Todo acá es cálculo
puro (sin DB): el router junta los datos de origen y le pasa listas/dicts
a estas funciones, así queda testeable sin base de datos y se recalcula
al vuelo cada vez que se pide, nunca queda un resultado "viejo" guardado."""

import dataclasses
import datetime

SEMANAS_POR_MES = 52 / 12  # ≈ 4.3333, tal como está validado en el Sheet


def lunes_de_semana(fecha: datetime.date) -> datetime.date:
    return fecha - datetime.timedelta(days=fecha.weekday())


def semanas_del_rango(desde: datetime.date, cantidad_semanas: int) -> list[datetime.date]:
    """Lista de lunes, empezando en la semana de ``desde``, ``cantidad_semanas``
    elementos."""
    inicio = lunes_de_semana(desde)
    return [inicio + datetime.timedelta(days=7 * i) for i in range(cantidad_semanas)]


def monto_plan_semanal(monto_mes_real: float) -> float:
    """Sección 2.2 (y su simétrico para compras): un monto mensual real
    repartido parejo entre las semanas del mes."""
    return monto_mes_real / SEMANAS_POR_MES


def gastos_generales_semanal(gastos_fijos_variables_mes: float, sueldos_mensual: float) -> float:
    """Sección 2.4: los sueldos NO se prorratean (se pagan completos en su
    semana), el resto de los gastos fijos/variables sí."""
    return (gastos_fijos_variables_mes - sueldos_mensual) / SEMANAS_POR_MES


def calcular_cobros(
    ventas_semana_actual: float, ventas_semana_anterior: float | None, pct_cobro_contado: float
) -> tuple[float, float]:
    """Sección 2.1, la regla real del negocio (no una estimación):
    70% de lo vendido se cobra la misma semana, 30% a los 7 días (se le
    asigna a la semana siguiente)."""
    cobro_contado = ventas_semana_actual * pct_cobro_contado
    cobro_ctacte = (ventas_semana_anterior or 0.0) * (1 - pct_cobro_contado)
    return cobro_contado, cobro_ctacte


def promedio_ventas_recientes(
    ventas_reales_por_semana: dict[datetime.date, float], semana_referencia: datetime.date, n_semanas: int = 4
) -> float | None:
    """Promedio de las últimas ``n_semanas`` con Ventas Real ya cerradas
    antes de ``semana_referencia``. None si todavía no hay ninguna (recién
    arrancó el plan)."""
    anteriores = sorted(s for s in ventas_reales_por_semana if s < semana_referencia)[-n_semanas:]
    if not anteriores:
        return None
    return sum(ventas_reales_por_semana[s] for s in anteriores) / len(anteriores)


def construir_ventas_plan_semanal(
    semanas: list[datetime.date],
    *,
    objetivos_por_mes: dict[tuple[int, int], float],
    ventas_reales_por_semana: dict[datetime.date, float],
    fallback_mensual: float,
) -> dict[datetime.date, float]:
    """VentasPlanSemanal por semana (no un único número fijo derivado del
    Cierre Estructural): prioriza el objetivo mensual vigente de cada mes
    (se recalibra solo, mes a mes, sin re-anclar el Cierre Estructural);
    si un mes todavía no tiene objetivo cargado, cae al promedio de las
    últimas semanas de Ventas Real; y si tampoco hay Real previo (arranque
    del plan), usa el fallback derivado del Cierre Estructural."""
    resultado: dict[datetime.date, float] = {}
    for semana in semanas:
        objetivo_mes = objetivos_por_mes.get((semana.year, semana.month))
        if objetivo_mes is not None:
            resultado[semana] = monto_plan_semanal(objetivo_mes)
            continue
        promedio = promedio_ventas_recientes(ventas_reales_por_semana, semana)
        resultado[semana] = promedio if promedio is not None else fallback_mensual
    return resultado


def estado_semaforo(flujo_acum_neto: float, umbral_riesgo: float, umbral_ajustado: float) -> str:
    if flujo_acum_neto < umbral_riesgo:
        return "riesgo"
    if flujo_acum_neto < umbral_ajustado:
        return "ajustado"
    return "ok"


@dataclasses.dataclass
class FilaCashflow:
    semana_inicio: datetime.date
    ventas_plan: float
    ventas_real: float | None
    ventas_usada: float
    cobro_contado: float
    cobro_ctacte: float
    compras_plan: float
    compras_real: float | None
    compras_usada: float
    pago_proveedores: float
    pago_cheques: float
    cuotas_bancarias: float
    sueldos_y_gastos: float
    total_ingresos: float
    total_egresos: float
    flujo_neto: float
    flujo_acum_bruto: float
    credito_usado: float
    flujo_acum_neto: float
    estado: str


def calcular_cashflow_semanal(
    semanas: list[datetime.date],
    *,
    ventas_reales_por_semana: dict[datetime.date, float],
    ventas_plan_semanal_monto: float,
    ventas_plan_por_semana: dict[datetime.date, float] | None = None,
    compras_reales_por_semana: dict[datetime.date, float],
    compras_plan_semanal_monto: float,
    pago_proveedores_por_semana: dict[datetime.date, float],
    pago_cheques_por_semana: dict[datetime.date, float],
    cuotas_por_semana: dict[datetime.date, float],
    sueldos_y_gastos_por_semana: dict[datetime.date, float],
    saldo_caja_inicial: float,
    credito_total: float,
    pct_cobro_contado: float,
    umbral_riesgo: float,
    umbral_ajustado: float,
) -> list[FilaCashflow]:
    """Sección 2.6, el corazón del modelo: por cada semana, en orden,
    flujo neto -> acumulado bruto -> crédito usado (ratchet, nunca se libera
    solo y nunca supera el total) -> acumulado neto -> semáforo."""
    filas: list[FilaCashflow] = []
    flujo_acum_bruto_prev = saldo_caja_inicial
    credito_usado_prev = 0.0
    ventas_usada_prev: float | None = None

    for semana in semanas:
        plan_semana = (ventas_plan_por_semana or {}).get(semana, ventas_plan_semanal_monto)
        ventas_real = ventas_reales_por_semana.get(semana)
        ventas_usada = ventas_real if ventas_real is not None else plan_semana

        cobro_contado, cobro_ctacte = calcular_cobros(ventas_usada, ventas_usada_prev, pct_cobro_contado)

        compras_real = compras_reales_por_semana.get(semana)
        compras_usada = compras_real if compras_real is not None else compras_plan_semanal_monto

        pago_proveedores = pago_proveedores_por_semana.get(semana, 0.0)
        pago_cheques = pago_cheques_por_semana.get(semana, 0.0)
        cuotas = cuotas_por_semana.get(semana, 0.0)
        sueldos_gastos = sueldos_y_gastos_por_semana.get(semana, 0.0)

        total_ingresos = cobro_contado + cobro_ctacte
        total_egresos = pago_proveedores + pago_cheques + cuotas + sueldos_gastos
        flujo_neto = total_ingresos - total_egresos

        flujo_acum_bruto = flujo_acum_bruto_prev + flujo_neto
        credito_usado = min(max(-flujo_acum_bruto, credito_usado_prev), credito_total)
        flujo_acum_neto = flujo_acum_bruto + credito_usado
        estado = estado_semaforo(flujo_acum_neto, umbral_riesgo, umbral_ajustado)

        filas.append(
            FilaCashflow(
                semana_inicio=semana,
                ventas_plan=plan_semana,
                ventas_real=ventas_real,
                ventas_usada=ventas_usada,
                cobro_contado=cobro_contado,
                cobro_ctacte=cobro_ctacte,
                compras_plan=compras_plan_semanal_monto,
                compras_real=compras_real,
                compras_usada=compras_usada,
                pago_proveedores=pago_proveedores,
                pago_cheques=pago_cheques,
                cuotas_bancarias=cuotas,
                sueldos_y_gastos=sueldos_gastos,
                total_ingresos=total_ingresos,
                total_egresos=total_egresos,
                flujo_neto=flujo_neto,
                flujo_acum_bruto=flujo_acum_bruto,
                credito_usado=credito_usado,
                flujo_acum_neto=flujo_acum_neto,
                estado=estado,
            )
        )

        flujo_acum_bruto_prev = flujo_acum_bruto
        credito_usado_prev = credito_usado
        ventas_usada_prev = ventas_usada

    return filas


def fecha_pago_compra(fecha_compra: datetime.date, plazo_dias: int | None) -> datetime.date | None:
    """Sección 2.3: fecha de pago = fecha de compra + plazo pactado. Si el
    proveedor no tiene plazo confirmado, devuelve None (se excluye del
    cálculo automático en vez de inventar un plazo)."""
    if plazo_dias is None:
        return None
    return fecha_compra + datetime.timedelta(days=plazo_dias)
