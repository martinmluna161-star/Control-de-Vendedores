"""agregar altas de clientes nuevos (módulo de gestión de clientes)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-09T12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'clientes_altas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('fecha', sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column('razon_social', sa.String(length=200), nullable=False),
        sa.Column('direccion', sa.String(length=300), nullable=True),
        sa.Column('zona_codigo', sa.String(length=10), sa.ForeignKey('zonas.codigo'), nullable=True),
        sa.Column('condicion_iva', sa.String(length=30), nullable=True),
        sa.Column('cuit_cuil', sa.String(length=20), nullable=True),
        sa.Column('ingresos_brutos_numero', sa.String(length=40), nullable=True),
        sa.Column('ramo', sa.String(length=120), nullable=True),
        sa.Column('telefono', sa.String(length=40), nullable=True),
        sa.Column('email', sa.String(length=200), nullable=True),
        sa.Column('horario', sa.String(length=120), nullable=True),
        sa.Column('observaciones', sa.String(length=1000), nullable=True),
        sa.Column('constancia_iva_archivo', sa.LargeBinary(), nullable=True),
        sa.Column('constancia_iva_nombre', sa.String(length=200), nullable=True),
        sa.Column('constancia_iva_tipo', sa.String(length=100), nullable=True),
        sa.Column('constancia_ingresos_brutos_archivo', sa.LargeBinary(), nullable=True),
        sa.Column('constancia_ingresos_brutos_nombre', sa.String(length=200), nullable=True),
        sa.Column('constancia_ingresos_brutos_tipo', sa.String(length=100), nullable=True),
        sa.Column('completo', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('completado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('mail_cortesia_enviado', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('creado_por', sa.String(length=10), sa.ForeignKey('vendedores.codigo_axum'), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_clientes_altas_creado_por', 'clientes_altas', ['creado_por'])
    op.create_index('ix_clientes_altas_completo', 'clientes_altas', ['completo'])


def downgrade() -> None:
    op.drop_index('ix_clientes_altas_completo', table_name='clientes_altas')
    op.drop_index('ix_clientes_altas_creado_por', table_name='clientes_altas')
    op.drop_table('clientes_altas')
