from app.services.metrics import (
    VentaPorFamilia,
    cobertura_por_familia,
    dias_habiles_mes,
    hora_a_segundos,
    matriz_cobertura_familia,
    objetivo_diario,
    objetivo_semanal,
    pct_avance_objetivo,
    pct_efectividad_ruta,
    ratio_conversion,
)


def test_avance_objetivo_normal():
    assert pct_avance_objetivo(monto_real=50_000, monto_objetivo=100_000) == 50.0


def test_avance_objetivo_supera_el_100():
    assert pct_avance_objetivo(monto_real=150_000, monto_objetivo=100_000) == 150.0


def test_avance_objetivo_sin_objetivo_cargado():
    assert pct_avance_objetivo(monto_real=1_000, monto_objetivo=0) is None


def test_efectividad_ruta_normal():
    assert pct_efectividad_ruta(visitas_efectivas=8, clientes_proyectados=10) == 80.0


def test_efectividad_ruta_sin_clientes_proyectados():
    assert pct_efectividad_ruta(visitas_efectivas=0, clientes_proyectados=0) is None


def test_cobertura_por_familia_reparte_porcentajes_sobre_el_total():
    ventas = [
        VentaPorFamilia(familia_id=1, familia_desc="PANIFICADOS", monto=300),
        VentaPorFamilia(familia_id=2, familia_desc="HELADOS", monto=100),
    ]
    resultado = cobertura_por_familia(ventas)

    assert [c.familia_desc for c in resultado] == ["PANIFICADOS", "HELADOS"]  # ordenado por monto desc
    assert resultado[0].porcentaje == 75.0
    assert resultado[1].porcentaje == 25.0


def test_cobertura_por_familia_sin_ventas_no_rompe():
    assert cobertura_por_familia([]) == []


def test_matriz_cobertura_familia_incluye_familias_solo_propuestas_y_solo_vendidas():
    matriz = matriz_cobertura_familia(
        ventas_por_familia={1: 500.0},
        proyecciones_por_familia={1: 3, 2: 5},
        nombres_familia={1: "PANIFICADOS", 2: "HELADOS"},
    )
    por_id = {fila.familia_id: fila for fila in matriz}

    assert por_id[1].monto_vendido == 500.0
    assert por_id[1].veces_proyectada == 3
    # familia 2 se propuso pero no se vendió nada: debe aparecer en 0, no desaparecer
    assert por_id[2].monto_vendido == 0.0
    assert por_id[2].veces_proyectada == 5


def test_ratio_conversion():
    assert ratio_conversion(visitas_realizadas=10, ventas_concretadas=4) == 40.0
    assert ratio_conversion(visitas_realizadas=0, ventas_concretadas=0) is None


def test_hora_a_segundos_formatos_validos():
    assert hora_a_segundos("09:00") == 9 * 3600
    assert hora_a_segundos("09:05:30") == 9 * 3600 + 5 * 60 + 30
    assert hora_a_segundos("00:00:00") == 0


def test_hora_a_segundos_invalido_da_none():
    assert hora_a_segundos(None) is None
    assert hora_a_segundos("") is None
    assert hora_a_segundos("NoVisito") is None


def test_dias_habiles_mes_excluye_domingos():
    # Septiembre 2026 tiene 30 días y 4 domingos.
    assert dias_habiles_mes(2026, 9) == 26


def test_objetivo_diario_y_semanal():
    diario = objetivo_diario(monto_objetivo=520_000, dias_habiles=26)
    assert diario == 20_000.0
    assert objetivo_semanal(diario) == 120_000.0


def test_objetivo_diario_sin_objetivo_da_none():
    assert objetivo_diario(monto_objetivo=None, dias_habiles=26) is None
    assert objetivo_diario(monto_objetivo=0, dias_habiles=26) is None
    assert objetivo_semanal(None) is None
