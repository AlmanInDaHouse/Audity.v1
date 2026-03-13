"""Add ai_orchestrator models

Revision ID: 0005_ai_orchestrator
Revises: 0004_rls_tenant_isolation
Create Date: 2026-03-12 13:42:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005_ai_orchestrator'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('task_type', sa.Enum('audit_fix', 'release_gate', 'hardening_task', name='tasktypeenum'), nullable=False),
        sa.Column('status', sa.Enum('requested', 'repo_snapshot_ready', 'claude_review_done', 'codex_patch_done', 'gemini_decision_done', 'executor_validation_done', 'approved', 'rejected', 'needs_second_round', 'failed', name='runstatusenum'), nullable=False),
        sa.Column('repo_commit', sa.String(length=64), nullable=True),
        sa.Column('base_branch', sa.String(length=255), nullable=True),
        sa.Column('working_branch', sa.String(length=255), nullable=True),
        sa.Column('requested_by', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_runs_org_id'), 'ai_runs', ['org_id'], unique=False)
    op.create_index(op.f('ix_ai_runs_project_id'), 'ai_runs', ['project_id'], unique=False)
    op.create_index(op.f('ix_ai_runs_status'), 'ai_runs', ['status'], unique=False)

    op.create_table(
        'ai_run_inputs',
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('scope_json', sa.JSON(), nullable=False),
        sa.Column('constraints_json', sa.JSON(), nullable=False),
        sa.Column('acceptance_criteria_json', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['ai_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('run_id')
    )

    op.create_table(
        'ai_agent_outputs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('agent_name', sa.Enum('claude', 'codex', 'gemini', 'executor', name='agentnameenum'), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('output_json', sa.JSON(), nullable=False),
        sa.Column('raw_text_ref', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['ai_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_agent_outputs_run_id'), 'ai_agent_outputs', ['run_id'], unique=False)

    op.create_table(
        'ai_patch_candidates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('proposed_by', sa.Enum('claude', 'codex', 'gemini', 'executor', name='agentnameenum'), nullable=False),
        sa.Column('diff_ref', sa.Text(), nullable=True),
        sa.Column('files_json', sa.JSON(), nullable=False),
        sa.Column('commands_json', sa.JSON(), nullable=False),
        sa.Column('risk_level', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['ai_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_patch_candidates_run_id'), 'ai_patch_candidates', ['run_id'], unique=False)

    op.create_table(
        'ai_guardrail_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('patch_id', sa.String(length=36), nullable=True),
        sa.Column('lint_passed', sa.Boolean(), nullable=False),
        sa.Column('tests_passed', sa.Boolean(), nullable=False),
        sa.Column('coverage_passed', sa.Boolean(), nullable=False),
        sa.Column('security_passed', sa.Boolean(), nullable=False),
        sa.Column('scope_passed', sa.Boolean(), nullable=False),
        sa.Column('details_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['patch_id'], ['ai_patch_candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['ai_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_guardrail_results_run_id'), 'ai_guardrail_results', ['run_id'], unique=False)

    op.create_table(
        'ai_decisions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('decided_by', sa.String(length=64), nullable=False),
        sa.Column('decision', sa.Enum('accept_claude', 'accept_codex', 'merge', 'second_round', name='decisionenum'), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('merged_plan_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['ai_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_decisions_run_id'), 'ai_decisions', ['run_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ai_decisions_run_id'), table_name='ai_decisions')
    op.drop_table('ai_decisions')
    op.drop_index(op.f('ix_ai_guardrail_results_run_id'), table_name='ai_guardrail_results')
    op.drop_table('ai_guardrail_results')
    op.drop_index(op.f('ix_ai_patch_candidates_run_id'), table_name='ai_patch_candidates')
    op.drop_table('ai_patch_candidates')
    op.drop_index(op.f('ix_ai_agent_outputs_run_id'), table_name='ai_agent_outputs')
    op.drop_table('ai_agent_outputs')
    op.drop_table('ai_run_inputs')
    op.drop_index(op.f('ix_ai_runs_status'), table_name='ai_runs')
    op.drop_index(op.f('ix_ai_runs_project_id'), table_name='ai_runs')
    op.drop_index(op.f('ix_ai_runs_org_id'), table_name='ai_runs')
    op.drop_table('ai_runs')

    sa.Enum(name='tasktypeenum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='runstatusenum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='agentnameenum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='decisionenum').drop(op.get_bind(), checkfirst=True)
