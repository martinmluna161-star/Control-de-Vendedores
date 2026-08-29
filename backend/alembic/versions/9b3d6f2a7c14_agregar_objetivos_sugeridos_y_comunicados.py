"""agregar objetivos_sugeridos y comunicados

Revision ID: 9b3d6f2a7c14
Revises: 7c2f4a9d1b3e
Create Date: 2026-08-29 00:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9b3d6f2a7c14'
down_revision: Union[str, None] = '7c2f4a9d1b3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'objetivos_sugeridos',
        sa.Column('vendedor_codigo', sa.String(length=10), sa.ForeignKey('vendedores.codigo_axum'), primary_key=True),
        sa.Column('anio', sa.Integer(), primary_key=True),
        sa.Column('mes', sa.Integer(), primary_key=True),
        sa.Column('objetivo_mes_anterior', sa.Numeric(14, 2), nullable=True),
        sa.Column('real_mes_anterior', sa.Numeric(14, 2), nullable=True),
        sa.Column('pct_cumplimiento_mes_anterior', sa.Numeric(6, 2), nullable=True),
        sa.Column('piso_recuperado', sa.Numeric(14, 2), nullable=True),
        sa.Column('crecimiento_aplicado_pct', sa.Numeric(6, 2), nullable=True),
        sa.Column('objetivo_sugerido', sa.Numeric(14, 2), nullable=False),
        sa.Column('variacion_vs_objetivo_anterior_pct', sa.Numeric(6, 2), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'comunicados',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('titulo', sa.String(length=200), nullable=False),
        sa.Column('detalle', sa.String(length=1000), nullable=True),
        sa.Column('vigente_desde', sa.Date(), nullable=False),
        sa.Column('vigente_hasta', sa.Date(), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('creado_por', sa.String(length=10), sa.ForeignKey('vendedores.codigo_axum'), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_comunicados_vigencia', 'comunicados', ['activo', 'vigente_desde', 'vigente_hasta'])


def downgrade() -> None:
    op.drop_index('ix_comunicados_vigencia', table_name='comunicados')
    op.drop_table('comunicados')
    op.drop_table('objetivos_sugeridos')
