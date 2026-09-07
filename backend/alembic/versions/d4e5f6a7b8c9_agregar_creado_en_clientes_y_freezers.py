"""agregar creado_en a clientes (para detectar "nuevo") y tabla de freezers por marca

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-07T14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clientes', sa.Column('creado_en', sa.DateTime(timezone=True), nullable=True))
    # Los clientes que ya existían no son "nuevos": se les pone una fecha
    # vieja fija en vez de la de hoy (que es lo que traería el default).
    op.execute("UPDATE clientes SET creado_en = '2020-01-01T00:00:00Z' WHERE creado_en IS NULL")
    op.alter_column('clientes', 'creado_en', nullable=False, server_default=sa.func.now())

    op.create_table(
        'clientes_freezers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cliente_codigo', sa.String(length=20), sa.ForeignKey('clientes.codigo'), nullable=False),
        sa.Column('marca', sa.String(length=10), nullable=False),
        sa.Column('cantidad_freezers', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('detalle_equipos', sa.Text(), nullable=True),
        sa.Column('ramo', sa.String(length=80), nullable=True),
        sa.Column('total_facturado', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('meses_activos', sa.Integer(), nullable=True),
        sa.Column('ultima_compra', sa.Date(), nullable=True),
        sa.Column('ranking', sa.Integer(), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('cliente_codigo', 'marca', name='uq_cliente_freezer_marca'),
    )
    op.create_index('ix_clientes_freezers_cliente', 'clientes_freezers', ['cliente_codigo'])


def downgrade() -> None:
    op.drop_index('ix_clientes_freezers_cliente', table_name='clientes_freezers')
    op.drop_table('clientes_freezers')
    op.drop_column('clientes', 'creado_en')
