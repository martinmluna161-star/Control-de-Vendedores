"""agregar módulo financiero (cashflow, compras, cheques, cuotas, gastos)

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-09-15T16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'financiero_cierre_estructural',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('fecha_corte', sa.Date(), nullable=False),
        sa.Column('ventas_netas_mes_real', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('compras_netas_mes_real', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('ar_bruto', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('ar_neto', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('deuda_proveedores', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('deuda_financiera', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('saldo_caja_bancos', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'financiero_parametros',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pct_cobro_contado', sa.Numeric(5, 4), nullable=False, server_default='0.70'),
        sa.Column('dias_cobro_ctacte', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('credito_total_disponible', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('umbral_riesgo', sa.Numeric(14, 2), nullable=False, server_default='5000000'),
        sa.Column('umbral_ajustado', sa.Numeric(14, 2), nullable=False, server_default='30000000'),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'financiero_proveedores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('nombre', sa.String(length=200), nullable=False, unique=True),
        sa.Column('plazo_dias', sa.Integer(), nullable=True),
        sa.Column('forma_pago_habitual', sa.String(length=20), nullable=False, server_default='cta_cte'),
        sa.Column('confirmado', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'financiero_compras',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('fecha_compra', sa.Date(), nullable=False),
        sa.Column('proveedor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('financiero_proveedores.id'), nullable=True),
        sa.Column('proveedor_nombre', sa.String(length=200), nullable=False),
        sa.Column('comprobante_numero', sa.String(length=60), nullable=True),
        sa.Column('monto', sa.Numeric(14, 2), nullable=False),
        sa.Column('forma_pago', sa.String(length=20), nullable=False, server_default='cta_cte'),
        sa.Column('fecha_pago_real', sa.Date(), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_financiero_compras_fecha', 'financiero_compras', ['fecha_compra'])

    op.create_table(
        'financiero_cheques',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('numero', sa.String(length=60), nullable=True),
        sa.Column('proveedor_nombre', sa.String(length=200), nullable=True),
        sa.Column('monto', sa.Numeric(14, 2), nullable=False),
        sa.Column('fecha_pago', sa.Date(), nullable=False),
        sa.Column('estado', sa.String(length=20), nullable=False, server_default='pendiente'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_financiero_cheques_fecha', 'financiero_cheques', ['fecha_pago'])

    op.create_table(
        'financiero_cuotas_bancarias',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('banco', sa.String(length=120), nullable=False),
        sa.Column('nro_cuota', sa.String(length=40), nullable=True),
        sa.Column('monto', sa.Numeric(14, 2), nullable=False),
        sa.Column('fecha_vencimiento', sa.Date(), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_financiero_cuotas_fecha', 'financiero_cuotas_bancarias', ['fecha_vencimiento'])

    op.create_table(
        'financiero_gastos_mensuales',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('anio', sa.Integer(), nullable=False),
        sa.Column('mes', sa.Integer(), nullable=False),
        sa.Column('sueldos_monto', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('semana_pago_sueldos', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('gastos_generales_monto', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('anio', 'mes', name='uq_financiero_gasto_mes'),
    )

    op.create_table(
        'financiero_impuestos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('nombre', sa.String(length=120), nullable=False),
        sa.Column('monto', sa.Numeric(14, 2), nullable=False),
        sa.Column('fecha_vencimiento', sa.Date(), nullable=False),
        sa.Column('pagado', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_financiero_impuestos_fecha', 'financiero_impuestos', ['fecha_vencimiento'])


def downgrade() -> None:
    op.drop_index('ix_financiero_impuestos_fecha', table_name='financiero_impuestos')
    op.drop_table('financiero_impuestos')
    op.drop_table('financiero_gastos_mensuales')
    op.drop_index('ix_financiero_cuotas_fecha', table_name='financiero_cuotas_bancarias')
    op.drop_table('financiero_cuotas_bancarias')
    op.drop_index('ix_financiero_cheques_fecha', table_name='financiero_cheques')
    op.drop_table('financiero_cheques')
    op.drop_index('ix_financiero_compras_fecha', table_name='financiero_compras')
    op.drop_table('financiero_compras')
    op.drop_table('financiero_proveedores')
    op.drop_table('financiero_parametros')
    op.drop_table('financiero_cierre_estructural')
