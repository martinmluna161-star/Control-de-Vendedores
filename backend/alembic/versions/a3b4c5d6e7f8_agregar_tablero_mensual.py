"""agregar tablero mensual: apertura fina de gastos/cuotas, escenarios, IIBB, markup

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-09-19T12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('financiero_cuotas_bancarias', sa.Column('capital_monto', sa.Numeric(14, 2), nullable=True))
    op.add_column('financiero_cuotas_bancarias', sa.Column('interes_monto', sa.Numeric(14, 2), nullable=True))

    op.add_column('financiero_gastos_mensuales', sa.Column('gastos_variables_monto', sa.Numeric(14, 2), nullable=True))
    op.add_column('financiero_gastos_mensuales', sa.Column('gastos_fijos_monto', sa.Numeric(14, 2), nullable=True))
    op.add_column('financiero_gastos_mensuales', sa.Column('casilla_monto', sa.Numeric(14, 2), nullable=True))
    op.add_column('financiero_gastos_mensuales', sa.Column('ingresos_brutos_monto', sa.Numeric(14, 2), nullable=True))
    op.add_column('financiero_gastos_mensuales', sa.Column('retiros_socios_monto', sa.Numeric(14, 2), nullable=True))
    op.add_column('financiero_gastos_mensuales', sa.Column('iva_monto', sa.Numeric(14, 2), nullable=True))

    op.create_table(
        'financiero_escenarios_proyeccion',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('nombre', sa.String(length=20), nullable=False, unique=True),
        sa.Column('crecimiento_ventas_mensual', sa.Numeric(6, 4), nullable=False),
        sa.Column('margen_bruto', sa.Numeric(6, 4), nullable=False),
        sa.Column('inflacion_gastos_mensual', sa.Numeric(6, 4), nullable=False),
        sa.Column('alicuota_iva', sa.Numeric(6, 4), nullable=False, server_default='0.21'),
        sa.Column('alicuota_ganancias', sa.Numeric(6, 4), nullable=False, server_default='0.35'),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'financiero_iibb_saldo_a_favor',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('fecha_corte', sa.Date(), nullable=False),
        sa.Column('saldo_a_favor', sa.Numeric(14, 2), nullable=False),
        sa.Column('impuesto_determinado_12m', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('retenido_12m', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'financiero_markup_linea',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('proveedor_o_linea', sa.String(length=200), nullable=False, unique=True),
        sa.Column('markup_pct', sa.Numeric(6, 4), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('financiero_markup_linea')
    op.drop_table('financiero_iibb_saldo_a_favor')
    op.drop_table('financiero_escenarios_proyeccion')

    op.drop_column('financiero_gastos_mensuales', 'iva_monto')
    op.drop_column('financiero_gastos_mensuales', 'retiros_socios_monto')
    op.drop_column('financiero_gastos_mensuales', 'ingresos_brutos_monto')
    op.drop_column('financiero_gastos_mensuales', 'casilla_monto')
    op.drop_column('financiero_gastos_mensuales', 'gastos_fijos_monto')
    op.drop_column('financiero_gastos_mensuales', 'gastos_variables_monto')

    op.drop_column('financiero_cuotas_bancarias', 'interes_monto')
    op.drop_column('financiero_cuotas_bancarias', 'capital_monto')
