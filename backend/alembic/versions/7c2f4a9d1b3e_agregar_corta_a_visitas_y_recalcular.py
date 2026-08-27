"""agregar columna corta a visitas_reales y recalcular valida/larga

Revision ID: 7c2f4a9d1b3e
Revises: 3a051630e155
Create Date: 2026-08-27 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c2f4a9d1b3e'
down_revision: Union[str, None] = '3a051630e155'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UMBRAL_CORTA_SEG = 60
UMBRAL_LARGA_SEG = 1800


def upgrade() -> None:
    op.add_column(
        'visitas_reales',
        sa.Column('corta', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Recalcula sobre los datos ya cargados con las reglas nuevas: una visita
    # de menos de 1 minuto no cuenta como "valida" (antes sí se contaba, con
    # tal de que hubiera check-in); el umbral de "larga" a revisar pasa de 5
    # a 30 minutos.
    op.execute(
        f"""
        UPDATE visitas_reales
        SET corta = valida AND tiempo_seg < {UMBRAL_CORTA_SEG},
            valida = valida AND tiempo_seg >= {UMBRAL_CORTA_SEG}
        """
    )
    op.execute(
        f"""
        UPDATE visitas_reales
        SET larga = valida AND tiempo_seg >= {UMBRAL_LARGA_SEG}
        """
    )
    op.alter_column('visitas_reales', 'corta', server_default=None)


def downgrade() -> None:
    op.drop_column('visitas_reales', 'corta')
