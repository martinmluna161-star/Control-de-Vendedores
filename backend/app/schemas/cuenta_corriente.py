import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class ResumenCargaCCOut(BaseModel):
    carga_id: uuid.UUID
    cantidad_registros: int
    clientes_procesados: int
    clientes_nuevos: list[str]
    vendedores_codigos: list[str]
    zonas_codigos: list[str]


class BitacoraCargaCCOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    creado_en: datetime.datetime
    usuario_nombre: str
    nombre_archivo: str
    tipo_archivo: str
    filtro_original: str | None
    cantidad_registros: int
    clientes_procesados: int
    vendedores_codigos: list[str]
    zonas_codigos: list[str]
    estado: str
    detalle_error: str | None


class ComprobanteCCOut(BaseModel):
    comprobante_numero: str | None
    comprobante_tipo: str | None
    fecha_comprobante: datetime.date | None
    fecha_vencimiento: datetime.date | None
    monto: float
    es_interes: bool
    fecha_interes: datetime.date | None
    nd_numero: str | None
    detalle_interes: str | None


class ClienteCCOut(BaseModel):
    cliente_codigo: str
    cliente_razon_social: str
    cliente_direccion: str | None
    zona_codigo: str | None
    vendedor_codigo: str | None
    vendedor_nombre: str | None
    monto_total_adeudado: float
    # Discriminado entre los comprobantes detallados: vencido (fecha de
    # vencimiento ya pasada) y por vencer (de hoy en adelante, o sin fecha
    # de vencimiento cargada). Si el cliente solo trae el saldo consolidado
    # (sin comprobantes detallados), todo el saldo queda como "por vencer".
    monto_vencido: float = 0
    monto_por_vencer: float = 0
    carga_fecha: datetime.datetime
    comprobantes: list[ComprobanteCCOut]
