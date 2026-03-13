"""pre-ga security closure

Revision ID: 0006_pre_ga_security_closure
Revises: 0005_ai_orchestrator
Create Date: 2026-03-13 10:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '0006_pre_ga_security_closure'
down_revision = '0005_ai_orchestrator'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('organizations', sa.Column('dpa_status', sa.String(length=32), nullable=False, server_default='pending'))
    op.add_column('organizations', sa.Column('dpa_signed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('organizations', sa.Column('dpa_reference', sa.String(length=255), nullable=True))
    op.add_column(
        'organizations',
        sa.Column('onboarding_status', sa.String(length=32), nullable=False, server_default='pending_dpa'),
    )
    op.add_column('organizations', sa.Column('onboarding_completed_at', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'secret_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('ciphertext', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_id', 'name', name='uq_secret_records_org_name'),
    )
    op.create_index('ix_secret_records_org_id', 'secret_records', ['org_id'], unique=False)

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        tenant_expr = "org_id::uuid = NULLIF(current_setting('app.current_org_id', true), '')::uuid"
        op.execute('ALTER TABLE secret_records ENABLE ROW LEVEL SECURITY;')
        op.execute('ALTER TABLE secret_records FORCE ROW LEVEL SECURITY;')
        op.execute('DROP POLICY IF EXISTS tenant_isolation_secret_records ON secret_records;')
        op.execute('DROP POLICY IF EXISTS tenant_isolation_secret_records_update ON secret_records;')
        op.execute('DROP POLICY IF EXISTS tenant_isolation_secret_records_delete ON secret_records;')
        op.execute('DROP POLICY IF EXISTS tenant_isolation_secret_records_insert ON secret_records;')
        op.execute(f'CREATE POLICY tenant_isolation_secret_records ON secret_records FOR SELECT USING ({tenant_expr});')
        op.execute(
            f'CREATE POLICY tenant_isolation_secret_records_update ON secret_records '
            f'FOR UPDATE USING ({tenant_expr}) WITH CHECK ({tenant_expr});'
        )
        op.execute(f'CREATE POLICY tenant_isolation_secret_records_delete ON secret_records FOR DELETE USING ({tenant_expr});')
        op.execute(
            f'CREATE POLICY tenant_isolation_secret_records_insert ON secret_records '
            f'FOR INSERT WITH CHECK ({tenant_expr});'
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP POLICY IF EXISTS tenant_isolation_secret_records_insert ON secret_records;')
        op.execute('DROP POLICY IF EXISTS tenant_isolation_secret_records_delete ON secret_records;')
        op.execute('DROP POLICY IF EXISTS tenant_isolation_secret_records_update ON secret_records;')
        op.execute('DROP POLICY IF EXISTS tenant_isolation_secret_records ON secret_records;')

    op.drop_index('ix_secret_records_org_id', table_name='secret_records')
    op.drop_table('secret_records')

    op.drop_column('organizations', 'onboarding_completed_at')
    op.drop_column('organizations', 'onboarding_status')
    op.drop_column('organizations', 'dpa_reference')
    op.drop_column('organizations', 'dpa_signed_at')
    op.drop_column('organizations', 'dpa_status')
