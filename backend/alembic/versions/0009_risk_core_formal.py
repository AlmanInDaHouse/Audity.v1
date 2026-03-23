"""risk core formal v1

Revision ID: 0009_risk_core_formal
Revises: 0008_catalog_versions
Create Date: 2026-03-23 19:30:00.000000
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0009_risk_core_formal'
down_revision = '0008_catalog_versions'
branch_labels = None
depends_on = None


DEFAULT_DIMENSIONS = (
    ('C', 'Confidencialidad', 'Impacto sobre la confidencialidad de la informacion', 0),
    ('I', 'Integridad', 'Impacto sobre la integridad de la informacion', 1),
    ('A', 'Disponibilidad', 'Impacto sobre la disponibilidad del servicio', 2),
    ('AUT', 'Autenticidad', 'Impacto sobre la autenticidad de identidades y datos', 3),
    ('TRAZ', 'Trazabilidad', 'Impacto sobre la trazabilidad y no repudio', 4),
)


def upgrade() -> None:
    criticality_enum = postgresql.ENUM('low', 'medium', 'high', name='criticalityenum', create_type=False)

    op.create_table(
        'security_dimension_profiles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'code', name='uq_security_dimension_profiles_project_code'),
    )
    op.create_index('ix_security_dimension_profiles_org_id', 'security_dimension_profiles', ['org_id'], unique=False)
    op.create_index('ix_security_dimension_profiles_project_id', 'security_dimension_profiles', ['project_id'], unique=False)

    op.create_table(
        'risk_assets',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('asset_type', sa.String(length=64), nullable=False, server_default='information'),
        sa.Column('owner', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column(
            'criticality',
            criticality_enum,
            nullable=False,
            server_default='medium',
        ),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_risk_assets_org_id', 'risk_assets', ['org_id'], unique=False)
    op.create_index('ix_risk_assets_project_id', 'risk_assets', ['project_id'], unique=False)

    op.create_table(
        'risk_threats',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False, server_default='generic'),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('source', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_risk_threats_org_id', 'risk_threats', ['org_id'], unique=False)
    op.create_index('ix_risk_threats_project_id', 'risk_threats', ['project_id'], unique=False)

    op.create_table(
        'risk_safeguards',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('safeguard_type', sa.String(length=64), nullable=False, server_default='control'),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='planned'),
        sa.Column('reference', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_risk_safeguards_org_id', 'risk_safeguards', ['org_id'], unique=False)
    op.create_index('ix_risk_safeguards_project_id', 'risk_safeguards', ['project_id'], unique=False)

    op.create_table(
        'risk_assessments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('methodology', sa.String(length=64), nullable=False, server_default='manual-v1'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='draft'),
        sa.Column('scope_summary', sa.Text(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('assessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_risk_assessments_org_id', 'risk_assessments', ['org_id'], unique=False)
    op.create_index('ix_risk_assessments_project_id', 'risk_assessments', ['project_id'], unique=False)

    op.create_table(
        'risk_asset_relations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('source_asset_id', sa.String(length=36), nullable=False),
        sa.Column('target_asset_id', sa.String(length=36), nullable=False),
        sa.Column('relation_type', sa.String(length=64), nullable=False, server_default='depends_on'),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_asset_id'], ['risk_assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_asset_id'], ['risk_assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_risk_asset_relations_org_id', 'risk_asset_relations', ['org_id'], unique=False)
    op.create_index('ix_risk_asset_relations_project_id', 'risk_asset_relations', ['project_id'], unique=False)
    op.create_index('ix_risk_asset_relations_source_asset_id', 'risk_asset_relations', ['source_asset_id'], unique=False)
    op.create_index('ix_risk_asset_relations_target_asset_id', 'risk_asset_relations', ['target_asset_id'], unique=False)

    op.create_table(
        'risk_scenarios',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('assessment_id', sa.String(length=36), nullable=False),
        sa.Column('asset_id', sa.String(length=36), nullable=True),
        sa.Column('threat_id', sa.String(length=36), nullable=True),
        sa.Column('safeguard_id', sa.String(length=36), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('likelihood', sa.String(length=32), nullable=True),
        sa.Column('impact', sa.String(length=32), nullable=True),
        sa.Column('risk_level', sa.String(length=32), nullable=True),
        sa.Column('dimension_values_json', sa.JSON(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['risk_assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asset_id'], ['risk_assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['safeguard_id'], ['risk_safeguards.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['threat_id'], ['risk_threats.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_risk_scenarios_org_id', 'risk_scenarios', ['org_id'], unique=False)
    op.create_index('ix_risk_scenarios_project_id', 'risk_scenarios', ['project_id'], unique=False)
    op.create_index('ix_risk_scenarios_assessment_id', 'risk_scenarios', ['assessment_id'], unique=False)
    op.create_index('ix_risk_scenarios_threat_id', 'risk_scenarios', ['threat_id'], unique=False)

    bind = op.get_bind()
    projects = list(bind.execute(sa.text('SELECT id, org_id FROM projects')))
    if projects:
        now = datetime.now(UTC)
        dimension_profiles = sa.table(
            'security_dimension_profiles',
            sa.column('id', sa.String(length=36)),
            sa.column('org_id', sa.String(length=36)),
            sa.column('project_id', sa.String(length=36)),
            sa.column('code', sa.String(length=16)),
            sa.column('name', sa.String(length=64)),
            sa.column('description', sa.Text()),
            sa.column('order_index', sa.Integer()),
            sa.column('is_active', sa.Boolean()),
            sa.column('created_at', sa.DateTime(timezone=True)),
            sa.column('updated_at', sa.DateTime(timezone=True)),
        )
        rows = []
        for project_id, org_id in projects:
            for code, name, description, order_index in DEFAULT_DIMENSIONS:
                rows.append(
                    {
                        'id': str(uuid.uuid4()),
                        'org_id': org_id,
                        'project_id': project_id,
                        'code': code,
                        'name': name,
                        'description': description,
                        'order_index': order_index,
                        'is_active': True,
                        'created_at': now,
                        'updated_at': now,
                    }
                )
        op.bulk_insert(dimension_profiles, rows)


def downgrade() -> None:
    op.drop_index('ix_risk_scenarios_threat_id', table_name='risk_scenarios')
    op.drop_index('ix_risk_scenarios_assessment_id', table_name='risk_scenarios')
    op.drop_index('ix_risk_scenarios_project_id', table_name='risk_scenarios')
    op.drop_index('ix_risk_scenarios_org_id', table_name='risk_scenarios')
    op.drop_table('risk_scenarios')

    op.drop_index('ix_risk_asset_relations_target_asset_id', table_name='risk_asset_relations')
    op.drop_index('ix_risk_asset_relations_source_asset_id', table_name='risk_asset_relations')
    op.drop_index('ix_risk_asset_relations_project_id', table_name='risk_asset_relations')
    op.drop_index('ix_risk_asset_relations_org_id', table_name='risk_asset_relations')
    op.drop_table('risk_asset_relations')

    op.drop_index('ix_risk_assessments_project_id', table_name='risk_assessments')
    op.drop_index('ix_risk_assessments_org_id', table_name='risk_assessments')
    op.drop_table('risk_assessments')

    op.drop_index('ix_risk_safeguards_project_id', table_name='risk_safeguards')
    op.drop_index('ix_risk_safeguards_org_id', table_name='risk_safeguards')
    op.drop_table('risk_safeguards')

    op.drop_index('ix_risk_threats_project_id', table_name='risk_threats')
    op.drop_index('ix_risk_threats_org_id', table_name='risk_threats')
    op.drop_table('risk_threats')

    op.drop_index('ix_risk_assets_project_id', table_name='risk_assets')
    op.drop_index('ix_risk_assets_org_id', table_name='risk_assets')
    op.drop_table('risk_assets')

    op.drop_index('ix_security_dimension_profiles_project_id', table_name='security_dimension_profiles')
    op.drop_index('ix_security_dimension_profiles_org_id', table_name='security_dimension_profiles')
    op.drop_table('security_dimension_profiles')
