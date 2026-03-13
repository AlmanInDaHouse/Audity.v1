"""world class production foundation

Revision ID: 0003_world_class_foundation
Revises: 0002_enterprise_hardening
Create Date: 2026-03-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '0003_world_class_foundation'
down_revision = '0002_enterprise_hardening'
branch_labels = None
depends_on = None


def _enable_rls(table: str, policy_sql: str) -> None:
    op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;')
    op.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY;')
    op.execute(f'DROP POLICY IF EXISTS p_{table}_tenant ON {table};')
    op.execute(f'CREATE POLICY p_{table}_tenant ON {table} USING ({policy_sql});')


def upgrade() -> None:
    op.execute("ALTER TYPE findingstatusenum ADD VALUE IF NOT EXISTS 'pending_validation';")

    op.create_table(
        'external_tickets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('finding_id', sa.String(36), sa.ForeignKey('findings.id', ondelete='CASCADE'), nullable=False),
        sa.Column(
            'outbound_integration_id',
            sa.String(36),
            sa.ForeignKey('outbound_integrations.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('provider', sa.String(64), nullable=False),
        sa.Column('external_key', sa.String(128), nullable=False),
        sa.Column('external_url', sa.String(1024), nullable=True),
        sa.Column('external_status', sa.String(64), nullable=False, server_default='open'),
        sa.Column('sync_state', sa.String(32), nullable=False, server_default='linked'),
        sa.Column('last_payload_json', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_external_tickets_org_id', 'external_tickets', ['org_id'])
    op.create_index('ix_external_tickets_finding_id', 'external_tickets', ['finding_id'])
    op.create_index('ix_external_tickets_outbound_integration_id', 'external_tickets', ['outbound_integration_id'])
    op.create_index('ix_external_tickets_external_key', 'external_tickets', ['external_key'])

    tenant_clause = (
        "org_id = current_setting('app.current_org_id', true) "
        "OR coalesce(current_setting('app.current_org_id', true), '') = ''"
    )
    _enable_rls('external_tickets', tenant_clause)


def downgrade() -> None:
    op.execute('ALTER TABLE external_tickets DISABLE ROW LEVEL SECURITY;')
    op.drop_index('ix_external_tickets_external_key', table_name='external_tickets')
    op.drop_index('ix_external_tickets_outbound_integration_id', table_name='external_tickets')
    op.drop_index('ix_external_tickets_finding_id', table_name='external_tickets')
    op.drop_index('ix_external_tickets_org_id', table_name='external_tickets')
    op.drop_table('external_tickets')
