"""agregar fecha_vencimiento real a financiero_compras

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-09-16T14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('financiero_compras', sa.Column('fecha_vencimiento', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('financiero_compras', 'fecha_vencimiento')
