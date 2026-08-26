"""agregar soporte a familias propuestas, familia_id en ventas y vendedor en visitas

Revision ID: 51824afef862
Revises: cb61d92daf67
Create Date: 2026-08-26 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51824afef862'
down_revision: Union[str, None] = 'cb61d92daf67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'proyeccion_diaria',
        sa.Column('familias_ids', sa.ARRAY(sa.Integer()), nullable=False, server_default='{}'),
    )

    op.add_column('ventas_detalle', sa.Column('familia_id', sa.Integer(), nullable=True))
    op.create_index('ix_ventas_detalle_familia_id', 'ventas_detalle', ['familia_id'])
    op.create_index('ix_ventas_detalle_vendedor_fecha', 'ventas_detalle', ['vendedor_codigo', 'fecha'])

    op.add_column('visitas_reales', sa.Column('vendedor_codigo', sa.String(length=10), nullable=True))
    op.create_foreign_key(
        'fk_visitas_reales_vendedor_codigo',
        'visitas_reales',
        'vendedores',
        ['vendedor_codigo'],
        ['codigo_axum'],
    )
    op.create_index('ix_visitas_reales_vendedor_fecha', 'visitas_reales', ['vendedor_codigo', 'fecha'])
    op.create_index('ix_visitas_reales_fecha', 'visitas_reales', ['fecha'])


def downgrade() -> None:
    op.drop_index('ix_visitas_reales_fecha', table_name='visitas_reales')
    op.drop_index('ix_visitas_reales_vendedor_fecha', table_name='visitas_reales')
    op.drop_constraint('fk_visitas_reales_vendedor_codigo', 'visitas_reales', type_='foreignkey')
    op.drop_column('visitas_reales', 'vendedor_codigo')

    op.drop_index('ix_ventas_detalle_vendedor_fecha', table_name='ventas_detalle')
    op.drop_index('ix_ventas_detalle_familia_id', table_name='ventas_detalle')
    op.drop_column('ventas_detalle', 'familia_id')

    op.drop_column('proyeccion_diaria', 'familias_ids')
