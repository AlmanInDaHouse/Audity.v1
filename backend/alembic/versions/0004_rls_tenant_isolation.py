"""RLS tenant isolation policies

Revision ID: 0004
Revises: 0003_world_class_foundation
Create Date: 2026-03-12 10:50:00.000000
"""
from alembic import op

revision = '0004'
down_revision = '0003_world_class_foundation'
branch_labels = None
depends_on = None

# All multi-tenant tables that have an org_id column.
TENANT_TABLES = [
    'projects',
    'integrations',
    'control_catalogs',
    'audit_runs',
    'findings',
    'evidence_items',
    'remediation_tasks',
    'auth_sessions',
    'org_security_policies',
    'scim_access_tokens',
    'role_permissions',
    'finding_approvals',
    'waivers',
    'remediation_comments',
    'outbound_integrations',
    'pricing_plans',
    'audit_packages',
    'external_tickets',
    'audit_log_entries',
    'memberships',
]


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}')

        # Policy: the application role 'audity' can only see rows
        # whose org_id matches the session variable app.current_org_id.
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table}
            ON {table}
            FOR ALL
            TO audity
            USING (org_id = current_setting('app.current_org_id', true))
            WITH CHECK (org_id = current_setting('app.current_org_id', true))
        """)

    # Special case: control_catalogs allows global catalogs (org_id IS NULL)
    op.execute('DROP POLICY tenant_isolation_control_catalogs ON control_catalogs')
    op.execute("""
        CREATE POLICY tenant_isolation_control_catalogs
        ON control_catalogs
        FOR ALL
        TO audity
        USING (
            org_id = current_setting('app.current_org_id', true)
            OR org_id IS NULL
        )
        WITH CHECK (
            org_id = current_setting('app.current_org_id', true)
            OR org_id IS NULL
        )
    """)

    # Special case: role_permissions allows global permissions (org_id IS NULL)
    op.execute('DROP POLICY tenant_isolation_role_permissions ON role_permissions')
    op.execute("""
        CREATE POLICY tenant_isolation_role_permissions
        ON role_permissions
        FOR ALL
        TO audity
        USING (
            org_id = current_setting('app.current_org_id', true)
            OR org_id IS NULL
        )
        WITH CHECK (
            org_id = current_setting('app.current_org_id', true)
            OR org_id IS NULL
        )
    """)


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}')
        op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY')
