"""agregar rutina diaria del supervisor (hoja de ruta editable + ejecución)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-12T16:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LV = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
LMV = ["Lunes", "Miércoles", "Viernes"]
MJ = ["Martes", "Jueves"]

# Modelo inicial de hoja de ruta provisto por el usuario -- queda 100%
# editable desde el módulo una vez cargado.
TAREAS_SEED = [
    (1, "Revisión Inicial", "07:50", "08:00", LV, "Lunes a Viernes",
     "Ver Venta de Camiones del Día",
     "Revisión del reporte de salidas de camiones y facturación del día anterior. Armado del temario para la reunión de ventas.",
     "Temario de reunión rápida listo"),
    (2, "Gestión de Equipo", "08:00", "09:00", LMV, "L-M-V",
     "Reunión Grupal de Vendedores",
     "Alineación comercial, comunicación de objetivos de la semana, capacitación en manejo de objeciones y revisión de cartera.",
     "Minuta de acuerdos y focos de venta"),
    (3, "Gestión de Equipo", "08:00", "09:00", MJ, "Martes y Jueves",
     "Gestión Individual / Coaching",
     "Acompañamiento y asistencia puntual a vendedores seleccionados con desvíos en cuota o cobranza.",
     "Plan de acción individual por vendedor"),
    (4, "Cuentas Corrientes", "09:00", "10:00", LV, "Lunes a Viernes",
     "Gestión de Ctas. Ctes. y Límites",
     "Análisis de cuentas corrientes propias y seguimiento de límites de crédito excedidos de la fuerza de ventas.",
     "Informe de cuentas liberadas / frenadas"),
    (5, "Auditoría Operativa", "10:00", "11:00", LV, "Lunes a Viernes",
     "Revisión de Actividad GPS",
     "Verificación de efectividad de ruteo, trazabilidad de visitas y cobertura en calle del equipo.",
     "Porcentaje de cumplimiento de ruta (GPS)"),
    (6, "Cobranzas Críticas", "11:00", "12:00", LV, "Lunes a Viernes",
     "Cobranzas de Cuentas Grandes",
     "Gestión directa sobre clientes clave y morosos para asegurar el flujo de caja diario.",
     "Monto recuperado / regularizado ($)"),
    (7, "Desarrollo Comercial", "12:00", "14:00", LMV, "L-M-V",
     "Gestión de Clientes Propios y Cierres",
     "Atención directa de clientes asignados y asistencia a vendedores en cierres estratégicos de ventas.",
     "Nuevos acuerdos de venta cerrados"),
    (8, "Desarrollo Comercial", "12:00", "14:00", MJ, "Martes y Jueves",
     "Negociaciones con Proveedores y Compras",
     "Revisión de acuerdos comerciales, negociación de promociones por volumen y solicitudes de apoyo en margen.",
     "Nuevos acuerdos / promociones negociadas"),
    (9, "Atención Zonas Remotas", "14:00", "15:00", ["Jueves"], "Jueves (o Miércoles cierre)",
     "Atención Villa Mercedes y Norte Grande",
     "Revisión de ruteos de distribución, efectividad de visitas en Villa Mercedes y estado de cartera en Norte Grande.",
     "Reporte operativo por zona remota"),
    (10, "Planificación y Stock", "14:00", "15:00", LMV, "L-M-V",
     "Proyección de Ventas vs. Stock",
     "Contraste de ventas proyectadas vs. inventario disponible y alineación de pedidos de abastecimiento.",
     "Listado de pedidos sugeridos de compra"),
    (11, "Cierre Operativo", "15:00", "16:00", LV, "Lunes a Viernes",
     "Visualización y Cierre de Ventas del Día",
     "Consolidación de ventas del día, medición del desvío vs. objetivo y preparación del día siguiente.",
     "Reporte final de facturación diaria ($)"),
]


def upgrade() -> None:
    op.create_table(
        'rutina_diaria_tareas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('orden', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('bloque_horario', sa.String(length=80), nullable=False),
        sa.Column('hora_inicio', sa.String(length=5), nullable=False),
        sa.Column('hora_fin', sa.String(length=5), nullable=False),
        sa.Column('dias_semana', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('tipo_dia_texto', sa.String(length=80), nullable=False, server_default=''),
        sa.Column('actividad_principal', sa.String(length=200), nullable=False),
        sa.Column('enfoque_detalle', sa.String(length=1000), nullable=True),
        sa.Column('entregables_kpis', sa.String(length=300), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'rutina_diaria_ejecuciones',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tarea_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rutina_diaria_tareas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.Column('observaciones', sa.String(length=500), nullable=True),
        sa.Column('marcado_por', sa.String(length=10), sa.ForeignKey('vendedores.codigo_axum'), nullable=False),
        sa.Column('marcado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('tarea_id', 'fecha', name='uq_rutina_tarea_fecha'),
    )
    op.create_index('ix_rutina_diaria_ejecuciones_tarea', 'rutina_diaria_ejecuciones', ['tarea_id'])

    tabla = sa.table(
        'rutina_diaria_tareas',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('orden', sa.Integer()),
        sa.column('bloque_horario', sa.String()),
        sa.column('hora_inicio', sa.String()),
        sa.column('hora_fin', sa.String()),
        sa.column('dias_semana', postgresql.ARRAY(sa.String())),
        sa.column('tipo_dia_texto', sa.String()),
        sa.column('actividad_principal', sa.String()),
        sa.column('enfoque_detalle', sa.String()),
        sa.column('entregables_kpis', sa.String()),
    )
    op.bulk_insert(
        tabla,
        [
            {
                "id": uuid.uuid4(),
                "orden": orden,
                "bloque_horario": bloque,
                "hora_inicio": hi,
                "hora_fin": hf,
                "dias_semana": dias,
                "tipo_dia_texto": tipo_dia,
                "actividad_principal": actividad,
                "enfoque_detalle": enfoque,
                "entregables_kpis": entregables,
            }
            for orden, bloque, hi, hf, dias, tipo_dia, actividad, enfoque, entregables in TAREAS_SEED
        ],
    )


def downgrade() -> None:
    op.drop_index('ix_rutina_diaria_ejecuciones_tarea', table_name='rutina_diaria_ejecuciones')
    op.drop_table('rutina_diaria_ejecuciones')
    op.drop_table('rutina_diaria_tareas')
