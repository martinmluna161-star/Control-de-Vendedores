"""agregar visible_en_selectores a vendedores

Revision ID: c1d2e3f4a5b6
Revises: 7b1d9e4f2a68
Create Date: 2026-10-10T00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = '7b1d9e4f2a68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'vendedores',
        sa.Column('visible_en_selectores', sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column('vendedores', 'visible_en_selectores')
