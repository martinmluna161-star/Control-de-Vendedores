"""agregar plan de cobertura de vacaciones

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-08T14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'vacaciones_planes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vendedor_codigo', sa.String(length=10), sa.ForeignKey('vendedores.codigo_axum'), nullable=False),
        sa.Column('fecha_desde', sa.Date(), nullable=False),
        sa.Column('fecha_hasta', sa.Date(), nullable=False),
        sa.Column('creado_por', sa.String(length=10), sa.ForeignKey('vendedores.codigo_axum'), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_vacaciones_planes_vendedor', 'vacaciones_planes', ['vendedor_codigo'])

    op.create_table(
        'vacaciones_planes_dias',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vacaciones_planes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('zona_codigo', sa.String(length=10), sa.ForeignKey('zonas.codigo'), nullable=False),
        sa.Column('vendedor_reemplazo_codigo', sa.String(length=10), sa.ForeignKey('vendedores.codigo_axum'), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('plan_id', 'fecha', 'zona_codigo', name='uq_vacaciones_dia_zona'),
    )
    op.create_index('ix_vacaciones_planes_dias_plan', 'vacaciones_planes_dias', ['plan_id'])

    op.create_table(
        'vacaciones_planes_clientes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('plan_dia_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vacaciones_planes_dias.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cliente_codigo', sa.String(length=20), sa.ForeignKey('clientes.codigo'), nullable=False),
        sa.Column('origenes', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('familias_ids', postgresql.ARRAY(sa.Integer()), nullable=False, server_default='{}'),
        sa.Column('observaciones', sa.String(length=500), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('plan_dia_id', 'cliente_codigo', name='uq_vacaciones_dia_cliente'),
    )
    op.create_index('ix_vacaciones_planes_clientes_dia', 'vacaciones_planes_clientes', ['plan_dia_id'])


def downgrade() -> None:
    op.drop_index('ix_vacaciones_planes_clientes_dia', table_name='vacaciones_planes_clientes')
    op.drop_table('vacaciones_planes_clientes')
    op.drop_index('ix_vacaciones_planes_dias_plan', table_name='vacaciones_planes_dias')
    op.drop_table('vacaciones_planes_dias')
    op.drop_index('ix_vacaciones_planes_vendedor', table_name='vacaciones_planes')
    op.drop_table('vacaciones_planes')
