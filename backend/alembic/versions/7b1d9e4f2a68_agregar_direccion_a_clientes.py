"""agregar dirección a clientes

Revision ID: 7b1d9e4f2a68
Revises: 453f06725f11
Create Date: 2026-10-02T00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7b1d9e4f2a68'
down_revision: Union[str, None] = '453f06725f11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clientes', sa.Column('direccion', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('clientes', 'direccion')
