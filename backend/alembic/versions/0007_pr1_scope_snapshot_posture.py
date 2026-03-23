"""pr1 scope snapshot posture

Revision ID: 0007_pr1_scope_snapshot_posture
Revises: 0006_pre_ga_security_closure
Create Date: 2026-03-23 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '0007_pr1_scope_snapshot_posture'
down_revision = '0006_pre_ga_security_closure'
branch_labels = None
depends_on = None


DEFAULT_FRAMEWORKS = ['ISO27001', 'ENS', 'RGPD']


def upgrade() -> None:
    with op.batch_alter_table('projects') as batch_op:
        batch_op.add_column(sa.Column('frameworks_json', sa.JSON(), nullable=True))

    with op.batch_alter_table('audit_runs') as batch_op:
        batch_op.add_column(sa.Column('frameworks_json', sa.JSON(), nullable=True))
    op.add_column('audit_runs', sa.Column('catalog_checksum', sa.String(length=64), nullable=True))
    op.add_column('audit_runs', sa.Column('catalog_snapshot_json', sa.JSON(), nullable=True))
    op.add_column('audit_runs', sa.Column('control_posture_score', sa.Float(), nullable=True))
    op.add_column('audit_runs', sa.Column('control_posture_level', sa.String(length=16), nullable=True))

    op.add_column('pricing_plans', sa.Column('max_projects', sa.Integer(), nullable=True))

    bind = op.get_bind()
    project_table = sa.table('projects', sa.column('frameworks_json', sa.JSON()))
    audit_run_table = sa.table(
        'audit_runs',
        sa.column('frameworks_json', sa.JSON()),
        sa.column('risk_score', sa.Float()),
        sa.column('risk_level', sa.String(length=16)),
        sa.column('control_posture_score', sa.Float()),
        sa.column('control_posture_level', sa.String(length=16)),
    )
    pricing_plan_table = sa.table(
        'pricing_plans',
        sa.column('max_assets', sa.Integer()),
        sa.column('max_projects', sa.Integer()),
    )

    bind.execute(
        project_table.update()
        .where(project_table.c.frameworks_json.is_(None))
        .values(frameworks_json=DEFAULT_FRAMEWORKS)
    )
    bind.execute(
        audit_run_table.update()
        .where(audit_run_table.c.frameworks_json.is_(None))
        .values(frameworks_json=DEFAULT_FRAMEWORKS)
    )
    op.execute(
        'UPDATE audit_runs '
        'SET control_posture_score = risk_score, control_posture_level = risk_level '
        'WHERE control_posture_score IS NULL OR control_posture_level IS NULL'
    )
    bind.execute(
        pricing_plan_table.update()
        .where(pricing_plan_table.c.max_projects.is_(None))
        .values(max_projects=pricing_plan_table.c.max_assets)
    )

    with op.batch_alter_table('projects') as batch_op:
        batch_op.alter_column('frameworks_json', existing_type=sa.JSON(), nullable=False)

    with op.batch_alter_table('audit_runs') as batch_op:
        batch_op.alter_column('frameworks_json', existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    op.drop_column('pricing_plans', 'max_projects')

    op.drop_column('audit_runs', 'control_posture_level')
    op.drop_column('audit_runs', 'control_posture_score')
    op.drop_column('audit_runs', 'catalog_snapshot_json')
    op.drop_column('audit_runs', 'catalog_checksum')
    op.drop_column('audit_runs', 'frameworks_json')

    op.drop_column('projects', 'frameworks_json')
