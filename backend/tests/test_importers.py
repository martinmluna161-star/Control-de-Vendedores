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


HTML_VISITA_CORTA = """<html><body>
<table id="gw_Reporte">
<tr><th>zona</th><th>codigo</th><th>Tiempo</th><th>razon_social</th><th>HoraMin</th><th>HoraMax</th><th>Fecha</th></tr>
<tr><td>1</td><td>500</td><td>0:40</td><td>CLIENTE VISITA CORTA</td><td>10:00:00</td><td>10:00:40</td><td>08/19/2026</td></tr>
</table>
</body></html>"""


HTML_TEXTO_TIEMPO_AMBIGUO = """<html><body>
<table id="gw_Reporte">
<tr><th>zona</th><th>codigo</th><th>Tiempo</th><th>razon_social</th><th>HoraMin</th><th>HoraMax</th><th>Fecha</th></tr>
<tr><td>1</td><td>501</td><td>79:25:00</td><td>CLIENTE VISITA LARGA</td><td>08:00:00</td><td>08:35:00</td><td>08/19/2026</td></tr>
</table>
</body></html>"""


def test_parse_visitas_html_deriva_duracion_de_horamin_horamax_no_del_texto():
    # El texto "Tiempo" de Axum puede venir en un formato ambiguo para
    # visitas largas (ej. "79:25:00" en vez de una duración real); HoraMin/
    # HoraMax es la fuente confiable y debe ganarle al texto.
    filas = parse_visitas_html(HTML_TEXTO_TIEMPO_AMBIGUO.encode("utf-8"))
    assert filas[0].tiempo_seg == 35 * 60  # 08:35:00 - 08:00:00, no lo que diga "79:25:00"


def test_parse_visitas_html_visita_de_menos_de_un_minuto():
    filas = parse_visitas_html(HTML_VISITA_CORTA.encode("utf-8"))
    assert filas[0].visitado is True
    assert filas[0].tiempo_seg == 40
