"""catalog versions

Revision ID: 0008_catalog_versions
Revises: 0007_pr1_scope_snapshot_posture
Create Date: 2026-03-23 18:00:00.000000
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

from app.catalog_engine import build_catalog_bundle, default_framework_scope

revision = '0008_catalog_versions'
down_revision = '0007_pr1_scope_snapshot_posture'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'catalog_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='draft'),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('frameworks_json', sa.JSON(), nullable=False),
        sa.Column('bundle_json', sa.JSON(), nullable=False),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_id', 'name', 'version', name='uq_catalog_versions_scope_name_version'),
    )
    op.create_index('ix_catalog_versions_org_id', 'catalog_versions', ['org_id'], unique=False)

    with op.batch_alter_table('audit_runs') as batch_op:
        batch_op.add_column(sa.Column('catalog_version_id', sa.String(length=36), nullable=True))
        batch_op.create_index('ix_audit_runs_catalog_version_id', ['catalog_version_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_audit_runs_catalog_version_id',
            'catalog_versions',
            ['catalog_version_id'],
            ['id'],
            ondelete='SET NULL',
        )

    bundle = build_catalog_bundle(default_framework_scope(), version='v1')
    catalog_versions = sa.table(
        'catalog_versions',
        sa.column('id', sa.String(length=36)),
        sa.column('org_id', sa.String(length=36)),
        sa.column('name', sa.String(length=255)),
        sa.column('version', sa.String(length=64)),
        sa.column('status', sa.String(length=32)),
        sa.column('checksum', sa.String(length=64)),
        sa.column('frameworks_json', sa.JSON()),
        sa.column('bundle_json', sa.JSON()),
        sa.column('created_by_user_id', sa.String(length=36)),
        sa.column('published_at', sa.DateTime(timezone=True)),
        sa.column('created_at', sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        catalog_versions,
        [
            {
                'id': str(uuid.uuid4()),
                'org_id': None,
                'name': 'core-catalog',
                'version': 'v1',
                'status': 'published',
                'checksum': bundle['checksum'],
                'frameworks_json': bundle['frameworks'],
                'bundle_json': bundle,
                'created_by_user_id': None,
                'published_at': datetime.now(UTC),
                'created_at': datetime.now(UTC),
            }
        ],
    )


def downgrade() -> None:
    with op.batch_alter_table('audit_runs') as batch_op:
        batch_op.drop_constraint('fk_audit_runs_catalog_version_id', type_='foreignkey')
        batch_op.drop_index('ix_audit_runs_catalog_version_id')
        batch_op.drop_column('catalog_version_id')

    op.drop_index('ix_catalog_versions_org_id', table_name='catalog_versions')
    op.drop_table('catalog_versions')
