from app.models.cliente import Cliente
from app.models.cuenta_corriente import CuentaCorrienteCarga, CuentaCorrienteComprobante
from app.models.novedad_zona import NovedadZona
from app.models.objetivo import ObjetivoMensual
from app.models.producto import ProductoFamilia
from app.models.proyeccion import ProyeccionDiaria
from app.models.venta import VentaDetalle, VentaTotalizada
from app.models.vendedor import Vendedor
from app.models.visita import VisitaReal
from app.models.zona import Zona

__all__ = [
    "Cliente",
    "CuentaCorrienteCarga",
    "CuentaCorrienteComprobante",
    "NovedadZona",
    "ObjetivoMensual",
    "ProductoFamilia",
    "ProyeccionDiaria",
    "VentaDetalle",
    "VentaTotalizada",
    "Vendedor",
    "VisitaReal",
    "Zona",
]
