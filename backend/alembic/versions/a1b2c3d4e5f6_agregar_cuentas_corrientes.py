"""agregar cuentas corrientes (bitacora de cargas y comprobantes)

Revision ID: a1b2c3d4e5f6
Revises: 4f7a2e9c8b31
Create Date: 2026-09-02 18:30:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '4f7a2e9c8b31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cuentas_corrientes_cargas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('usuario_auth_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('usuario_nombre', sa.String(length=120), nullable=False),
        sa.Column('nombre_archivo', sa.String(length=300), nullable=False),
        sa.Column('tipo_archivo', sa.String(length=20), nullable=False),
        sa.Column('filtro_original', sa.String(length=300), nullable=True),
        sa.Column('cantidad_registros', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('clientes_procesados', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('vendedores_codigos', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('zonas_codigos', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.Column('detalle_error', sa.Text(), nullable=True),
    )
    op.create_index('ix_cc_cargas_creado_en', 'cuentas_corrientes_cargas', ['creado_en'])

    op.create_table(
        'cuentas_corrientes_comprobantes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            'carga_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('cuentas_corrientes_cargas.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('cliente_codigo', sa.String(length=20), sa.ForeignKey('clientes.codigo'), nullable=False),
        sa.Column('cliente_razon_social', sa.String(length=200), nullable=False),
        sa.Column('cliente_direccion', sa.String(length=300), nullable=True),
        sa.Column('zona_codigo', sa.String(length=10), sa.ForeignKey('zonas.codigo'), nullable=True),
        sa.Column('vendedor_codigo', sa.String(length=10), sa.ForeignKey('vendedores.codigo_axum'), nullable=True),
        sa.Column('monto_total_cliente', sa.Numeric(14, 2), nullable=False),
        sa.Column('comprobante_numero', sa.String(length=40), nullable=True),
        sa.Column('comprobante_tipo', sa.String(length=10), nullable=True),
        sa.Column('fecha_comprobante', sa.Date(), nullable=True),
        sa.Column('fecha_vencimiento', sa.Date(), nullable=True),
        sa.Column('monto', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('es_interes', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('fecha_interes', sa.Date(), nullable=True),
        sa.Column('nd_numero', sa.String(length=40), nullable=True),
        sa.Column('detalle_interes', sa.String(length=300), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_cc_comprobantes_carga', 'cuentas_corrientes_comprobantes', ['carga_id'])
    op.create_index('ix_cc_comprobantes_cliente', 'cuentas_corrientes_comprobantes', ['cliente_codigo'])
    op.create_index('ix_cc_comprobantes_vendedor', 'cuentas_corrientes_comprobantes', ['vendedor_codigo'])


def downgrade() -> None:
    op.drop_index('ix_cc_comprobantes_vendedor', table_name='cuentas_corrientes_comprobantes')
    op.drop_index('ix_cc_comprobantes_cliente', table_name='cuentas_corrientes_comprobantes')
    op.drop_index('ix_cc_comprobantes_carga', table_name='cuentas_corrientes_comprobantes')
    op.drop_table('cuentas_corrientes_comprobantes')
    op.drop_index('ix_cc_cargas_creado_en', table_name='cuentas_corrientes_cargas')
    op.drop_table('cuentas_corrientes_cargas')
