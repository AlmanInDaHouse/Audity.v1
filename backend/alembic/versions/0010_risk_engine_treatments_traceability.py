"""risk engine, treatments and traceability

Revision ID: 0010_risk_engine_trc
Revises: 0009_risk_core_formal
Create Date: 2026-03-23 21:10:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '0010_risk_engine_trc'
down_revision = '0009_risk_core_formal'
branch_labels = None
depends_on = None


def _enforce_core_tenant_isolation(table: str) -> None:
    tenant_expr = "org_id::uuid = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
    op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;')
    op.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY;')
    op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table} ON {table};')
    op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table}_update ON {table};')
    op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table}_delete ON {table};')
    op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table}_insert ON {table};')
    op.execute(f'CREATE POLICY tenant_isolation_{table} ON {table} FOR SELECT USING ({tenant_expr});')
    op.execute(
        f'CREATE POLICY tenant_isolation_{table}_update ON {table} '
        f'FOR UPDATE USING ({tenant_expr}) WITH CHECK ({tenant_expr});'
    )
    op.execute(f'CREATE POLICY tenant_isolation_{table}_delete ON {table} FOR DELETE USING ({tenant_expr});')
    op.execute(f'CREATE POLICY tenant_isolation_{table}_insert ON {table} FOR INSERT WITH CHECK ({tenant_expr});')


def upgrade() -> None:
    op.create_table(
        'risk_treatment_decisions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('assessment_id', sa.String(length=36), nullable=False),
        sa.Column('scenario_id', sa.String(length=36), nullable=False),
        sa.Column('safeguard_id', sa.String(length=36), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('decision', sa.String(length=32), nullable=False, server_default='mitigate'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='proposed'),
        sa.Column('applies_to', sa.String(length=32), nullable=False, server_default='both'),
        sa.Column('effectiveness_pct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rationale', sa.Text(), nullable=False, server_default=''),
        sa.Column('implementation_notes', sa.Text(), nullable=False, server_default=''),
        sa.Column('owner_user_id', sa.String(length=36), nullable=True),
        sa.Column('decided_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['risk_assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['decided_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['safeguard_id'], ['risk_safeguards.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['scenario_id'], ['risk_scenarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_risk_treatment_decisions_org_id', 'risk_treatment_decisions', ['org_id'], unique=False)
    op.create_index('ix_risk_treatment_decisions_project_id', 'risk_treatment_decisions', ['project_id'], unique=False)
    op.create_index('ix_risk_treatment_decisions_assessment_id', 'risk_treatment_decisions', ['assessment_id'], unique=False)
    op.create_index('ix_risk_treatment_decisions_scenario_id', 'risk_treatment_decisions', ['scenario_id'], unique=False)

    op.create_table(
        'risk_scenario_evaluations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('assessment_id', sa.String(length=36), nullable=False),
        sa.Column('scenario_id', sa.String(length=36), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('engine_version', sa.String(length=32), nullable=False, server_default='deterministic-v1'),
        sa.Column('inherent_likelihood', sa.String(length=32), nullable=False),
        sa.Column('inherent_impact', sa.String(length=32), nullable=False),
        sa.Column('inherent_score', sa.Float(), nullable=False),
        sa.Column('inherent_level', sa.String(length=32), nullable=False),
        sa.Column('residual_likelihood', sa.String(length=32), nullable=False),
        sa.Column('residual_impact', sa.String(length=32), nullable=False),
        sa.Column('residual_score', sa.Float(), nullable=False),
        sa.Column('residual_level', sa.String(length=32), nullable=False),
        sa.Column('input_snapshot_json', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column('trace_json', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column('notes', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['risk_assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scenario_id'], ['risk_scenarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('scenario_id', 'version', name='uq_risk_scenario_evaluations_scenario_version'),
    )
    op.create_index('ix_risk_scenario_evaluations_org_id', 'risk_scenario_evaluations', ['org_id'], unique=False)
    op.create_index('ix_risk_scenario_evaluations_project_id', 'risk_scenario_evaluations', ['project_id'], unique=False)
    op.create_index('ix_risk_scenario_evaluations_assessment_id', 'risk_scenario_evaluations', ['assessment_id'], unique=False)
    op.create_index('ix_risk_scenario_evaluations_scenario_id', 'risk_scenario_evaluations', ['scenario_id'], unique=False)

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        _enforce_core_tenant_isolation('risk_treatment_decisions')
        _enforce_core_tenant_isolation('risk_scenario_evaluations')


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        for table in ['risk_scenario_evaluations', 'risk_treatment_decisions']:
            op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table}_insert ON {table};')
            op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table}_delete ON {table};')
            op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table}_update ON {table};')
            op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table} ON {table};')
            op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;')

    op.drop_index('ix_risk_scenario_evaluations_scenario_id', table_name='risk_scenario_evaluations')
    op.drop_index('ix_risk_scenario_evaluations_assessment_id', table_name='risk_scenario_evaluations')
    op.drop_index('ix_risk_scenario_evaluations_project_id', table_name='risk_scenario_evaluations')
    op.drop_index('ix_risk_scenario_evaluations_org_id', table_name='risk_scenario_evaluations')
    op.drop_table('risk_scenario_evaluations')

    op.drop_index('ix_risk_treatment_decisions_scenario_id', table_name='risk_treatment_decisions')
    op.drop_index('ix_risk_treatment_decisions_assessment_id', table_name='risk_treatment_decisions')
    op.drop_index('ix_risk_treatment_decisions_project_id', table_name='risk_treatment_decisions')
    op.drop_index('ix_risk_treatment_decisions_org_id', table_name='risk_treatment_decisions')
    op.drop_table('risk_treatment_decisions')
