from app.services.importers import parse_visitas_html

HTML_EJEMPLO = """<html><body>
<table id="gw_Reporte">
<tr><th>zona</th><th>codigo</th><th>Tiempo (mm:ss)</th><th>razon_social</th><th>HoraMin</th><th>HoraMax</th><th>Fecha</th></tr>
<tr><td>01</td><td>472</td><td>0</td><td>CLIENTE NO VISITADO</td><td>NoVisito</td><td>NoVisito</td><td>NoVisito</td></tr>
<tr><td>1</td><td>3.608</td><td>5:30</td><td>CLIENTE VISITADO</td><td>09:00:00</td><td>09:05:30</td><td>08/19/2026</td></tr>
</table>
</body></html>"""


def test_parse_visitas_html_distingue_visitado_de_no_visitado():
    filas = parse_visitas_html(HTML_EJEMPLO.encode("utf-8"))
    assert len(filas) == 2

    no_visitada, visitada = filas
    assert no_visitada.visitado is False
    assert no_visitada.hora_min is None
    assert no_visitada.tiempo_seg == 0

    assert visitada.visitado is True
    assert visitada.cliente_codigo == "3608"  # el punto de miles se limpia
    assert visitada.tiempo_seg == 5 * 60 + 30
    assert visitada.hora_min == "09:00:00"


def test_parse_visitas_html_sin_tabla_esperada_da_error_claro():
    import pytest

    with pytest.raises(ValueError):
        parse_visitas_html(b"<html><body>sin tabla</body></html>")
