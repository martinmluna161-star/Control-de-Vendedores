"""agregar tipo "aviso" a comunicados con respuesta del vendedor y cierre

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-07T18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('comunicados', sa.Column('respuesta_vendedor', sa.String(length=1000), nullable=True))
    op.add_column('comunicados', sa.Column('respuesta_en', sa.DateTime(timezone=True), nullable=True))
    op.add_column('comunicados', sa.Column('cerrado', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('comunicados', sa.Column('cerrado_en', sa.DateTime(timezone=True), nullable=True))
    op.add_column('comunicados', sa.Column('cerrado_por', sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column('comunicados', 'cerrado_por')
    op.drop_column('comunicados', 'cerrado_en')
    op.drop_column('comunicados', 'cerrado')
    op.drop_column('comunicados', 'respuesta_en')
    op.drop_column('comunicados', 'respuesta_vendedor')
