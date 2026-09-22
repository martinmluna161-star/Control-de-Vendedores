"""agregar hilo de mensajes (chat) a los avisos de comunicados

Revision ID: f7a8b9c0d1e2
Revises: a3b4c5d6e7f8
Create Date: 2026-09-22T00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'comunicado_mensajes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('comunicado_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('comunicados.id'), nullable=False),
        sa.Column('autor_codigo', sa.String(length=10), sa.ForeignKey('vendedores.codigo_axum'), nullable=False),
        sa.Column('texto', sa.String(length=1000), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Migra la única respuesta que ya tenía cada aviso (el viejo esquema de
    # "una sola respuesta") al nuevo hilo, como su primer mensaje.
    op.execute("""
        INSERT INTO comunicado_mensajes (id, comunicado_id, autor_codigo, texto, creado_en)
        SELECT gen_random_uuid(), id, destinatarios_codigos[1], respuesta_vendedor, respuesta_en
        FROM comunicados
        WHERE tipo = 'aviso' AND respuesta_vendedor IS NOT NULL
    """)

    op.drop_column('comunicados', 'respuesta_vendedor')
    op.drop_column('comunicados', 'respuesta_en')


def downgrade() -> None:
    op.add_column('comunicados', sa.Column('respuesta_vendedor', sa.String(length=1000), nullable=True))
    op.add_column('comunicados', sa.Column('respuesta_en', sa.DateTime(timezone=True), nullable=True))
    op.drop_table('comunicado_mensajes')
