from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models import CriticalityEnum


def _normalize_dimension_code(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise ValueError('dimension code cannot be empty')
    return normalized


def _normalize_keyword(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError('value cannot be empty')
    return normalized


class SecurityDimensionProfileCreate(BaseModel):
    code: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=64)
    description: str = ''
    order_index: int = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator('code')
    @classmethod
    def validate_code(cls, value: str) -> str:
        return _normalize_dimension_code(value)


class SecurityDimensionProfileUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=16)
    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = None
    order_index: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator('code')
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_dimension_code(value)


class RiskAssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    asset_type: str = Field(default='information', min_length=1, max_length=64)
    owner: str | None = Field(default=None, max_length=255)
    description: str = ''
    criticality: CriticalityEnum = CriticalityEnum.medium
    metadata_json: dict = Field(default_factory=dict)


class RiskAssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    asset_type: str | None = Field(default=None, min_length=1, max_length=64)
    owner: str | None = Field(default=None, max_length=255)
    description: str | None = None
    criticality: CriticalityEnum | None = None
    metadata_json: dict | None = None


class RiskAssetRelationCreate(BaseModel):
    source_asset_id: str
    target_asset_id: str
    relation_type: str = Field(default='depends_on', min_length=1, max_length=64)
    description: str = ''


class RiskAssetRelationUpdate(BaseModel):
    source_asset_id: str | None = None
    target_asset_id: str | None = None
    relation_type: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = None


class RiskThreatCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(default='generic', min_length=1, max_length=64)
    description: str = ''
    source: str | None = Field(default=None, max_length=128)


class RiskThreatUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = None
    source: str | None = Field(default=None, max_length=128)


class RiskSafeguardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    safeguard_type: str = Field(default='control', min_length=1, max_length=64)
    description: str = ''
    status: str = Field(default='planned', min_length=1, max_length=32)
    reference: str | None = Field(default=None, max_length=255)


class RiskSafeguardUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    safeguard_type: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = None
    status: str | None = Field(default=None, min_length=1, max_length=32)
    reference: str | None = Field(default=None, max_length=255)


class RiskAssessmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    methodology: str = Field(default='manual-v1', min_length=1, max_length=64)
    status: str = Field(default='draft', min_length=1, max_length=32)
    scope_summary: str = ''
    notes: str = ''
    assessed_at: datetime | None = None


class RiskAssessmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    methodology: str | None = Field(default=None, min_length=1, max_length=64)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    scope_summary: str | None = None
    notes: str | None = None
    assessed_at: datetime | None = None


class RiskScenarioCreate(BaseModel):
    assessment_id: str
    asset_id: str | None = None
    threat_id: str | None = None
    safeguard_id: str | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str = ''
    likelihood: str | None = Field(default=None, max_length=32)
    impact: str | None = Field(default=None, max_length=32)
    risk_level: str | None = Field(default=None, max_length=32)
    dimension_values_json: dict[str, str] = Field(default_factory=dict)
    notes: str = ''


class RiskScenarioUpdate(BaseModel):
    assessment_id: str | None = None
    asset_id: str | None = None
    threat_id: str | None = None
    safeguard_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    likelihood: str | None = Field(default=None, max_length=32)
    impact: str | None = Field(default=None, max_length=32)
    risk_level: str | None = Field(default=None, max_length=32)
    dimension_values_json: dict[str, str] | None = None
    notes: str | None = None


class RiskTreatmentDecisionCreate(BaseModel):
    safeguard_id: str | None = None
    title: str = Field(min_length=1, max_length=255)
    decision: str = Field(default='mitigate', min_length=1, max_length=32)
    status: str = Field(default='proposed', min_length=1, max_length=32)
    applies_to: str = Field(default='both', min_length=1, max_length=32)
    effectiveness_pct: int = Field(default=0, ge=0, le=100)
    rationale: str = ''
    implementation_notes: str = ''
    owner_user_id: str | None = None
    due_date: datetime | None = None
    review_due_at: datetime | None = None
    metadata_json: dict = Field(default_factory=dict)

    @field_validator('decision', 'status', 'applies_to')
    @classmethod
    def validate_keywords(cls, value: str) -> str:
        return _normalize_keyword(value)


class RiskTreatmentDecisionUpdate(BaseModel):
    safeguard_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    decision: str | None = Field(default=None, min_length=1, max_length=32)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    applies_to: str | None = Field(default=None, min_length=1, max_length=32)
    effectiveness_pct: int | None = Field(default=None, ge=0, le=100)
    rationale: str | None = None
    implementation_notes: str | None = None
    owner_user_id: str | None = None
    due_date: datetime | None = None
    review_due_at: datetime | None = None
    metadata_json: dict | None = None

    @field_validator('decision', 'status', 'applies_to')
    @classmethod
    def validate_optional_keywords(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_keyword(value)


class RiskScenarioEvaluationCreate(BaseModel):
    notes: str = ''
    treatment_ids: list[str] = Field(default_factory=list)
