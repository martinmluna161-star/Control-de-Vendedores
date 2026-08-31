"""agregar desarrollo_clientes_nuevos y destinatarios en comunicados

Revision ID: 4f7a2e9c8b31
Revises: 9b3d6f2a7c14
Create Date: 2026-08-30 12:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4f7a2e9c8b31'
down_revision: Union[str, None] = '9b3d6f2a7c14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('comunicados', sa.Column('destinatarios_codigos', postgresql.ARRAY(sa.String()), nullable=True))

    op.create_table(
        'desarrollo_clientes_nuevos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vendedor_codigo', sa.String(length=10), sa.ForeignKey('vendedores.codigo_axum'), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('nombre_lugar', sa.String(length=200), nullable=False),
        sa.Column('zona_codigo', sa.String(length=10), sa.ForeignKey('zonas.codigo'), nullable=True),
        sa.Column('direccion', sa.String(length=300), nullable=True),
        sa.Column('fotos', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('detalle_visita', sa.String(length=1000), nullable=True),
        sa.Column('completado', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completado_en', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'ix_desarrollo_clientes_vendedor_fecha', 'desarrollo_clientes_nuevos', ['vendedor_codigo', 'fecha']
    )
    op.create_index('ix_desarrollo_clientes_completado', 'desarrollo_clientes_nuevos', ['completado'])


def downgrade() -> None:
    op.drop_index('ix_desarrollo_clientes_completado', table_name='desarrollo_clientes_nuevos')
    op.drop_index('ix_desarrollo_clientes_vendedor_fecha', table_name='desarrollo_clientes_nuevos')
    op.drop_table('desarrollo_clientes_nuevos')
    op.drop_column('comunicados', 'destinatarios_codigos')
