"""agregar hash de contenido a cargas de cuenta corriente (detectar duplicados)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-05T13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cuentas_corrientes_cargas', sa.Column('contenido_hash', sa.String(length=64), nullable=True))
    op.create_index('ix_cc_cargas_contenido_hash', 'cuentas_corrientes_cargas', ['contenido_hash'])


def downgrade() -> None:
    op.drop_index('ix_cc_cargas_contenido_hash', table_name='cuentas_corrientes_cargas')
    op.drop_column('cuentas_corrientes_cargas', 'contenido_hash')
