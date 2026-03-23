from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models import CriticalityEnum, utc_now, uuid_str

CANONICAL_DIMENSION_CODES: tuple[str, ...] = ('C', 'I', 'A', 'AUT', 'TRAZ')
RISK_TABLE_NAMES: frozenset[str] = frozenset(
    {
        'security_dimension_profiles',
        'risk_assets',
        'risk_asset_relations',
        'risk_threats',
        'risk_safeguards',
        'risk_assessments',
        'risk_scenarios',
        'risk_treatment_decisions',
        'risk_scenario_evaluations',
    }
)


class SecurityDimensionProfile(Base):
    __tablename__ = 'security_dimension_profiles'
    __table_args__ = (UniqueConstraint('project_id', 'code', name='uq_security_dimension_profiles_project_code'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, default='')
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class RiskAsset(Base):
    __tablename__ = 'risk_assets'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(64), default='information')
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, default='')
    criticality: Mapped[CriticalityEnum] = mapped_column(Enum(CriticalityEnum), default=CriticalityEnum.medium)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class RiskAssetRelation(Base):
    __tablename__ = 'risk_asset_relations'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    source_asset_id: Mapped[str] = mapped_column(String(36), ForeignKey('risk_assets.id', ondelete='CASCADE'), index=True)
    target_asset_id: Mapped[str] = mapped_column(String(36), ForeignKey('risk_assets.id', ondelete='CASCADE'), index=True)
    relation_type: Mapped[str] = mapped_column(String(64), default='depends_on')
    description: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RiskThreat(Base):
    __tablename__ = 'risk_threats'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default='generic')
    description: Mapped[str] = mapped_column(Text, default='')
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class RiskSafeguard(Base):
    __tablename__ = 'risk_safeguards'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    safeguard_type: Mapped[str] = mapped_column(String(64), default='control')
    description: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(32), default='planned')
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class RiskAssessment(Base):
    __tablename__ = 'risk_assessments'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    methodology: Mapped[str] = mapped_column(String(64), default='manual-v1')
    status: Mapped[str] = mapped_column(String(32), default='draft')
    scope_summary: Mapped[str] = mapped_column(Text, default='')
    notes: Mapped[str] = mapped_column(Text, default='')
    assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class RiskScenario(Base):
    __tablename__ = 'risk_scenarios'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    assessment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('risk_assessments.id', ondelete='CASCADE'), index=True
    )
    asset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey('risk_assets.id', ondelete='SET NULL'), nullable=True)
    threat_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey('risk_threats.id', ondelete='SET NULL'), nullable=True, index=True
    )
    safeguard_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey('risk_safeguards.id', ondelete='SET NULL'), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default='')
    likelihood: Mapped[str | None] = mapped_column(String(32), nullable=True)
    impact: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dimension_values_json: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class RiskTreatmentDecision(Base):
    __tablename__ = 'risk_treatment_decisions'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    assessment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('risk_assessments.id', ondelete='CASCADE'), index=True
    )
    scenario_id: Mapped[str] = mapped_column(String(36), ForeignKey('risk_scenarios.id', ondelete='CASCADE'), index=True)
    safeguard_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey('risk_safeguards.id', ondelete='SET NULL'), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), default='mitigate')
    status: Mapped[str] = mapped_column(String(32), default='proposed')
    applies_to: Mapped[str] = mapped_column(String(32), default='both')
    effectiveness_pct: Mapped[int] = mapped_column(Integer, default=0)
    rationale: Mapped[str] = mapped_column(Text, default='')
    implementation_notes: Mapped[str] = mapped_column(Text, default='')
    owner_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    decided_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class RiskScenarioEvaluation(Base):
    __tablename__ = 'risk_scenario_evaluations'
    __table_args__ = (UniqueConstraint('scenario_id', 'version', name='uq_risk_scenario_evaluations_scenario_version'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    assessment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('risk_assessments.id', ondelete='CASCADE'), index=True
    )
    scenario_id: Mapped[str] = mapped_column(String(36), ForeignKey('risk_scenarios.id', ondelete='CASCADE'), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    engine_version: Mapped[str] = mapped_column(String(32), default='deterministic-v1')
    inherent_likelihood: Mapped[str] = mapped_column(String(32), nullable=False)
    inherent_impact: Mapped[str] = mapped_column(String(32), nullable=False)
    inherent_score: Mapped[float] = mapped_column(nullable=False)
    inherent_level: Mapped[str] = mapped_column(String(32), nullable=False)
    residual_likelihood: Mapped[str] = mapped_column(String(32), nullable=False)
    residual_impact: Mapped[str] = mapped_column(String(32), nullable=False)
    residual_score: Mapped[float] = mapped_column(nullable=False)
    residual_level: Mapped[str] = mapped_column(String(32), nullable=False)
    input_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    trace_json: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default='')
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
