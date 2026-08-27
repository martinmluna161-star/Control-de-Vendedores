"""agregar observaciones a proyeccion diaria

Revision ID: 3a051630e155
Revises: 51824afef862
Create Date: 2026-08-27 01:45:50.916255

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a051630e155'
down_revision: Union[str, None] = '51824afef862'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('proyeccion_diaria', sa.Column('observaciones', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('proyeccion_diaria', 'observaciones')
