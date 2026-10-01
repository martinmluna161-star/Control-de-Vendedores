import datetime

from app.routers.quickfoods import _hace_n_meses
from app.services.quickfoods import calcular_cobertura, tipo_pdv


def test_tipo_pdv_aass():
    assert tipo_pdv("AUTOSERVICIOS") == "aass"
    assert tipo_pdv("SUPERMERCADOS") == "aass"


def test_tipo_pdv_almacenes():
    assert tipo_pdv("ALMACENES") == "almacenes"


def test_tipo_pdv_fuera_del_panel():
    assert tipo_pdv("KIOSCOS") is None
    assert tipo_pdv("GASTRONOMICOS") is None
    assert tipo_pdv(None) is None


def test_calcular_cobertura_hamburguesas_aass():
    # Igual al ejemplo real: 95% de obj. cob., universo 12, 11 compradores.
    filas = calcular_cobertura("aass", universo_gtm_total=12, compradores_por_familia={9: 11})
    hamburguesas = next(f for f in filas if f.familia_id == 9)
    assert hamburguesas.obj_cob_pct == 95.0
    assert hamburguesas.ccc_obj == 11  # round(95% * 12) = round(11.4) = 11
    assert hamburguesas.ccc == 11
    assert hamburguesas.clientes_faltan == 0
    assert hamburguesas.real_gtm_pct == round(11 / 12 * 100, 2)


def test_calcular_cobertura_usa_objetivo_de_almacenes_no_el_de_aass():
    filas = calcular_cobertura("almacenes", universo_gtm_total=29, compradores_por_familia={9: 27})
    hamburguesas = next(f for f in filas if f.familia_id == 9)
    assert hamburguesas.obj_cob_pct == 80.0  # no 95.0 (ese es el de AASS)
    assert hamburguesas.ccc_obj == round(0.80 * 29)


def test_calcular_cobertura_sin_compradores_da_cero_sin_explotar():
    filas = calcular_cobertura("aass", universo_gtm_total=12, compradores_por_familia={})
    for fila in filas:
        assert fila.ccc == 0
        assert fila.clientes_faltan == fila.ccc_obj


def test_calcular_cobertura_universo_cero_no_divide_por_cero():
    filas = calcular_cobertura("aass", universo_gtm_total=0, compradores_por_familia={})
    for fila in filas:
        assert fila.real_gtm_pct is None
        assert fila.ccc_obj == 0


def test_calcular_cobertura_clientes_faltan_nunca_negativo():
    # Si por algún motivo compraron más de lo "necesario" para el objetivo.
    filas = calcular_cobertura("almacenes", universo_gtm_total=29, compradores_por_familia={5: 29})
    papas = next(f for f in filas if f.familia_id == 5)
    assert papas.ccc == 29
    assert papas.clientes_faltan == 0


def test_carne_in_natura_porcina_no_tiene_fila():
    filas = calcular_cobertura("aass", universo_gtm_total=10, compradores_por_familia={})
    assert all(f.familia_id != 34 for f in filas)


def test_hace_n_meses_caso_simple():
    assert _hace_n_meses(datetime.date(2026, 9, 30), 3) == datetime.date(2026, 6, 30)


def test_hace_n_meses_cruza_año():
    assert _hace_n_meses(datetime.date(2026, 1, 15), 3) == datetime.date(2025, 10, 15)


def test_hace_n_meses_clampea_dia_inexistente():
    # El 31 de agosto, 3 meses atrás es "31 de mayo" -- mayo sí tiene 31.
    assert _hace_n_meses(datetime.date(2026, 8, 31), 3) == datetime.date(2026, 5, 31)
    # Pero 3 meses antes del 31 de diciembre caerían en "31 de septiembre",
    # que no existe -- se clampea al último día real (30).
    assert _hace_n_meses(datetime.date(2026, 12, 31), 3) == datetime.date(2026, 9, 30)
