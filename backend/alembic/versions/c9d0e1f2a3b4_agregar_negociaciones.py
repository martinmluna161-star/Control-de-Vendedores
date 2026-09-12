"""agregar negociaciones especiales (aprobación de supervisor/admin)

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-09-13T10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'negociaciones',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vendedor_codigo', sa.String(length=10), sa.ForeignKey('vendedores.codigo_axum'), nullable=False),
        sa.Column('cliente_codigo', sa.String(length=20), sa.ForeignKey('clientes.codigo'), nullable=True),
        sa.Column('cliente_nombre', sa.String(length=200), nullable=True),
        sa.Column('titulo', sa.String(length=200), nullable=False),
        sa.Column('detalle', sa.String(length=2000), nullable=False),
        sa.Column('estado', sa.String(length=20), nullable=False, server_default='pendiente'),
        sa.Column('respuesta_supervisor', sa.String(length=2000), nullable=True),
        sa.Column('respondido_por', sa.String(length=10), sa.ForeignKey('vendedores.codigo_axum'), nullable=True),
        sa.Column('respondido_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('email_enviado', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('destinatarios_email_extra', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('visto_por_vendedor', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_negociaciones_vendedor', 'negociaciones', ['vendedor_codigo'])
    op.create_index('ix_negociaciones_estado', 'negociaciones', ['estado'])


def downgrade() -> None:
    op.drop_index('ix_negociaciones_estado', table_name='negociaciones')
    op.drop_index('ix_negociaciones_vendedor', table_name='negociaciones')
    op.drop_table('negociaciones')
