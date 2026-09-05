"""agregar comentarios de cobranza y envío de mail para comunicados

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-05T15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cobranza_comentarios',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cliente_codigo', sa.String(length=20), sa.ForeignKey('clientes.codigo'), nullable=False),
        sa.Column('cliente_razon_social', sa.String(length=200), nullable=False),
        sa.Column('vendedor_codigo', sa.String(length=10), sa.ForeignKey('vendedores.codigo_axum'), nullable=True),
        sa.Column('vendedor_nombre', sa.String(length=120), nullable=False),
        sa.Column('comentario', sa.Text(), nullable=False),
        sa.Column('monto_adeudado', sa.Numeric(14, 2), nullable=True),
        sa.Column('leido', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('leido_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('leido_por', sa.String(length=120), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_cobranza_comentarios_cliente', 'cobranza_comentarios', ['cliente_codigo'])
    op.create_index('ix_cobranza_comentarios_leido', 'cobranza_comentarios', ['leido'])

    op.add_column('comunicados', sa.Column('enviar_email', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('comunicados', sa.Column('destinatarios_email', postgresql.ARRAY(sa.String()), nullable=True))


def downgrade() -> None:
    op.drop_column('comunicados', 'destinatarios_email')
    op.drop_column('comunicados', 'enviar_email')
    op.drop_index('ix_cobranza_comentarios_leido', table_name='cobranza_comentarios')
    op.drop_index('ix_cobranza_comentarios_cliente', table_name='cobranza_comentarios')
    op.drop_table('cobranza_comentarios')
