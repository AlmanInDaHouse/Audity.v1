from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLogEntry, Membership, Project
from app.risk.engine import TreatmentInput, evaluate_scenario, normalize_scale_value
from app.risk.models import (
    CANONICAL_DIMENSION_CODES,
    RiskAssessment,
    RiskAsset,
    RiskAssetRelation,
    RiskSafeguard,
    RiskScenario,
    RiskScenarioEvaluation,
    RiskThreat,
    RiskTreatmentDecision,
    SecurityDimensionProfile,
)
from app.risk.schemas import (
    RiskAssessmentCreate,
    RiskAssessmentUpdate,
    RiskAssetCreate,
    RiskAssetRelationCreate,
    RiskAssetRelationUpdate,
    RiskAssetUpdate,
    RiskSafeguardCreate,
    RiskSafeguardUpdate,
    RiskScenarioCreate,
    RiskScenarioEvaluationCreate,
    RiskScenarioUpdate,
    RiskTreatmentDecisionCreate,
    RiskTreatmentDecisionUpdate,
    RiskThreatCreate,
    RiskThreatUpdate,
    SecurityDimensionProfileCreate,
    SecurityDimensionProfileUpdate,
)

DEFAULT_DIMENSION_PROFILES: tuple[dict[str, Any], ...] = (
    {'code': 'C', 'name': 'Confidencialidad', 'description': 'Impacto sobre la confidencialidad de la informacion', 'order_index': 0},
    {'code': 'I', 'name': 'Integridad', 'description': 'Impacto sobre la integridad de la informacion', 'order_index': 1},
    {'code': 'A', 'name': 'Disponibilidad', 'description': 'Impacto sobre la disponibilidad del servicio', 'order_index': 2},
    {'code': 'AUT', 'name': 'Autenticidad', 'description': 'Impacto sobre la autenticidad de identidades y datos', 'order_index': 3},
    {'code': 'TRAZ', 'name': 'Trazabilidad', 'description': 'Impacto sobre la trazabilidad y no repudio', 'order_index': 4},
)


async def get_project_for_org(db: AsyncSession, *, org_id: str, project_id: str) -> Project:
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.org_id == org_id))
    if project is None:
        raise HTTPException(status_code=404, detail='Project not found')
    return project


def security_dimension_profile_to_dict(item: SecurityDimensionProfile) -> dict[str, Any]:
    return {
        'id': item.id,
        'org_id': item.org_id,
        'project_id': item.project_id,
        'code': item.code,
        'name': item.name,
        'description': item.description,
        'order_index': item.order_index,
        'is_active': item.is_active,
        'created_at': item.created_at.isoformat(),
        'updated_at': item.updated_at.isoformat(),
    }


def risk_asset_to_dict(item: RiskAsset) -> dict[str, Any]:
    return {
        'id': item.id,
        'org_id': item.org_id,
        'project_id': item.project_id,
        'name': item.name,
        'asset_type': item.asset_type,
        'owner': item.owner,
        'description': item.description,
        'criticality': item.criticality.value,
        'metadata_json': item.metadata_json,
        'created_at': item.created_at.isoformat(),
        'updated_at': item.updated_at.isoformat(),
    }


def risk_asset_relation_to_dict(item: RiskAssetRelation) -> dict[str, Any]:
    return {
        'id': item.id,
        'org_id': item.org_id,
        'project_id': item.project_id,
        'source_asset_id': item.source_asset_id,
        'target_asset_id': item.target_asset_id,
        'relation_type': item.relation_type,
        'description': item.description,
        'created_at': item.created_at.isoformat(),
    }


def risk_threat_to_dict(item: RiskThreat) -> dict[str, Any]:
    return {
        'id': item.id,
        'org_id': item.org_id,
        'project_id': item.project_id,
        'name': item.name,
        'category': item.category,
        'description': item.description,
        'source': item.source,
        'created_at': item.created_at.isoformat(),
        'updated_at': item.updated_at.isoformat(),
    }


def risk_safeguard_to_dict(item: RiskSafeguard) -> dict[str, Any]:
    return {
        'id': item.id,
        'org_id': item.org_id,
        'project_id': item.project_id,
        'name': item.name,
        'safeguard_type': item.safeguard_type,
        'description': item.description,
        'status': item.status,
        'reference': item.reference,
        'created_at': item.created_at.isoformat(),
        'updated_at': item.updated_at.isoformat(),
    }


def risk_assessment_to_dict(item: RiskAssessment) -> dict[str, Any]:
    return {
        'id': item.id,
        'org_id': item.org_id,
        'project_id': item.project_id,
        'name': item.name,
        'methodology': item.methodology,
        'status': item.status,
        'scope_summary': item.scope_summary,
        'notes': item.notes,
        'assessed_at': item.assessed_at.isoformat() if item.assessed_at else None,
        'created_by_user_id': item.created_by_user_id,
        'created_at': item.created_at.isoformat(),
        'updated_at': item.updated_at.isoformat(),
    }


def risk_scenario_to_dict(item: RiskScenario) -> dict[str, Any]:
    return {
        'id': item.id,
        'org_id': item.org_id,
        'project_id': item.project_id,
        'assessment_id': item.assessment_id,
        'asset_id': item.asset_id,
        'threat_id': item.threat_id,
        'safeguard_id': item.safeguard_id,
        'title': item.title,
        'description': item.description,
        'likelihood': item.likelihood,
        'impact': item.impact,
        'risk_level': item.risk_level,
        'dimension_values_json': item.dimension_values_json,
        'notes': item.notes,
        'created_at': item.created_at.isoformat(),
        'updated_at': item.updated_at.isoformat(),
    }


def risk_treatment_decision_to_dict(item: RiskTreatmentDecision) -> dict[str, Any]:
    return {
        'id': item.id,
        'org_id': item.org_id,
        'project_id': item.project_id,
        'assessment_id': item.assessment_id,
        'scenario_id': item.scenario_id,
        'safeguard_id': item.safeguard_id,
        'title': item.title,
        'decision': item.decision,
        'status': item.status,
        'applies_to': item.applies_to,
        'effectiveness_pct': item.effectiveness_pct,
        'rationale': item.rationale,
        'implementation_notes': item.implementation_notes,
        'owner_user_id': item.owner_user_id,
        'decided_by_user_id': item.decided_by_user_id,
        'due_date': item.due_date.isoformat() if item.due_date else None,
        'review_due_at': item.review_due_at.isoformat() if item.review_due_at else None,
        'metadata_json': item.metadata_json,
        'created_at': item.created_at.isoformat(),
        'updated_at': item.updated_at.isoformat(),
    }


def risk_scenario_evaluation_to_dict(item: RiskScenarioEvaluation) -> dict[str, Any]:
    return {
        'id': item.id,
        'org_id': item.org_id,
        'project_id': item.project_id,
        'assessment_id': item.assessment_id,
        'scenario_id': item.scenario_id,
        'version': item.version,
        'engine_version': item.engine_version,
        'inherent_likelihood': item.inherent_likelihood,
        'inherent_impact': item.inherent_impact,
        'inherent_score': item.inherent_score,
        'inherent_level': item.inherent_level,
        'residual_likelihood': item.residual_likelihood,
        'residual_impact': item.residual_impact,
        'residual_score': item.residual_score,
        'residual_level': item.residual_level,
        'input_snapshot_json': item.input_snapshot_json,
        'trace_json': item.trace_json,
        'notes': item.notes,
        'created_by_user_id': item.created_by_user_id,
        'created_at': item.created_at.isoformat(),
    }


def audit_log_entry_to_dict(item: AuditLogEntry) -> dict[str, Any]:
    return {
        'id': item.id,
        'org_id': item.org_id,
        'actor_user_id': item.actor_user_id,
        'action': item.action,
        'entity_type': item.entity_type,
        'entity_id': item.entity_id,
        'payload_json': item.payload_json,
        'prev_hash': item.prev_hash,
        'entry_hash': item.entry_hash,
        'created_at': item.created_at.isoformat(),
    }


def _audit_log_matches_scenario(item: AuditLogEntry, *, scenario_id: str) -> bool:
    if item.entity_id == scenario_id:
        return True
    payload = item.payload_json or {}
    return payload.get('scenario_id') == scenario_id


def is_canonical_dimension_code(code: str) -> bool:
    return code in CANONICAL_DIMENSION_CODES


def _normalize_treatment_fields(
    *,
    decision: str,
    status: str,
    applies_to: str,
    effectiveness_pct: int,
) -> dict[str, Any]:
    allowed_decisions = {'mitigate', 'accept', 'avoid', 'transfer'}
    allowed_statuses = {'proposed', 'approved', 'in_progress', 'implemented', 'accepted', 'rejected', 'retired'}
    allowed_scopes = {'none', 'likelihood', 'impact', 'both'}

    if decision not in allowed_decisions:
        raise HTTPException(status_code=400, detail=f'Unsupported treatment decision: {decision}')
    if status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f'Unsupported treatment status: {status}')
    if applies_to not in allowed_scopes:
        raise HTTPException(status_code=400, detail=f'Unsupported treatment applies_to: {applies_to}')

    normalized_applies_to = applies_to
    normalized_effectiveness = effectiveness_pct
    if decision == 'accept':
        normalized_applies_to = 'none'
        normalized_effectiveness = 0
    elif decision == 'avoid':
        normalized_applies_to = 'none'
    elif decision == 'transfer' and applies_to == 'both':
        normalized_applies_to = 'impact'

    return {
        'decision': decision,
        'status': status,
        'applies_to': normalized_applies_to,
        'effectiveness_pct': normalized_effectiveness,
    }


def _is_scenario_evaluation_version_conflict(exc: IntegrityError) -> bool:
    details = ' '.join(
        part
        for part in (
            str(getattr(exc, 'orig', '') or ''),
            str(getattr(exc, 'statement', '') or ''),
            str(getattr(exc, 'params', '') or ''),
        )
        if part
    ).lower()
    return (
        'uq_risk_scenario_evaluations_scenario_version' in details
        or 'risk_scenario_evaluations.scenario_id, risk_scenario_evaluations.version' in details
        or ('risk_scenario_evaluations' in details and 'version' in details and 'unique' in details)
    )


async def _validate_owner_user_membership(db: AsyncSession, *, org_id: str, owner_user_id: str | None) -> None:
    if owner_user_id is None:
        return
    membership = await db.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == owner_user_id)
    )
    if membership is None:
        raise HTTPException(status_code=400, detail='owner_user_id must belong to the same organization')


def _normalize_formal_scale(value: str | None, *, field_name: str) -> str | None:
    try:
        return normalize_scale_value(value, field_name=field_name, required=False)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _normalize_dimension_scale_values(dimension_values_json: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for code, raw_value in dimension_values_json.items():
        try:
            normalized[code] = str(normalize_scale_value(raw_value, field_name=f'dimension {code}', required=True))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return normalized


async def _lock_scenario_for_evaluation(db: AsyncSession, *, scenario: RiskScenario) -> None:
    await db.scalar(
        select(RiskScenario.id)
        .where(
            RiskScenario.id == scenario.id,
            RiskScenario.org_id == scenario.org_id,
            RiskScenario.project_id == scenario.project_id,
        )
        .with_for_update()
    )


async def _flush_risk_scenario_evaluation_insert(db: AsyncSession) -> None:
    await db.flush()


async def _list_dimension_profiles(db: AsyncSession, *, org_id: str, project_id: str) -> list[SecurityDimensionProfile]:
    return (
        await db.execute(
            select(SecurityDimensionProfile)
            .where(
                SecurityDimensionProfile.org_id == org_id,
                SecurityDimensionProfile.project_id == project_id,
            )
            .order_by(SecurityDimensionProfile.order_index.asc(), SecurityDimensionProfile.code.asc())
        )
    ).scalars().all()


async def ensure_default_dimension_profiles(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    commit: bool = False,
) -> list[SecurityDimensionProfile]:
    rows = await _list_dimension_profiles(db, org_id=org_id, project_id=project_id)
    existing_codes = {row.code for row in rows}
    missing = [item for item in DEFAULT_DIMENSION_PROFILES if item['code'] not in existing_codes]

    if missing:
        nested = await db.begin_nested()
        try:
            db.add_all(
                [
                    SecurityDimensionProfile(
                        org_id=org_id,
                        project_id=project_id,
                        code=item['code'],
                        name=item['name'],
                        description=item['description'],
                        order_index=item['order_index'],
                        is_active=True,
                    )
                    for item in missing
                ]
            )
            await db.flush()
        except IntegrityError:
            await nested.rollback()
        else:
            await nested.commit()
    if commit:
        await db.commit()
    return await _list_dimension_profiles(db, org_id=org_id, project_id=project_id)


async def list_dimension_profiles(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    ensure_defaults: bool = False,
) -> list[SecurityDimensionProfile]:
    if ensure_defaults:
        return await ensure_default_dimension_profiles(db, org_id=org_id, project_id=project_id, commit=False)
    return await _list_dimension_profiles(db, org_id=org_id, project_id=project_id)


async def get_dimension_profile(db: AsyncSession, *, org_id: str, project_id: str, dimension_id: str) -> SecurityDimensionProfile:
    item = await db.scalar(
        select(SecurityDimensionProfile).where(
            SecurityDimensionProfile.id == dimension_id,
            SecurityDimensionProfile.org_id == org_id,
            SecurityDimensionProfile.project_id == project_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail='Security dimension profile not found')
    return item


async def create_dimension_profile(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    payload: SecurityDimensionProfileCreate,
) -> SecurityDimensionProfile:
    existing = await db.scalar(
        select(SecurityDimensionProfile).where(
            SecurityDimensionProfile.org_id == org_id,
            SecurityDimensionProfile.project_id == project_id,
            SecurityDimensionProfile.code == payload.code,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=400, detail='Security dimension code already exists for project')
    item = SecurityDimensionProfile(
        org_id=org_id,
        project_id=project_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        order_index=payload.order_index,
        is_active=payload.is_active,
    )
    db.add(item)
    await db.flush()
    return item


async def update_dimension_profile(
    db: AsyncSession,
    *,
    item: SecurityDimensionProfile,
    payload: SecurityDimensionProfileUpdate,
) -> SecurityDimensionProfile:
    if is_canonical_dimension_code(item.code):
        if payload.code is not None and payload.code != item.code:
            raise HTTPException(status_code=400, detail='Canonical security dimensions cannot change code')
        if payload.is_active is False:
            raise HTTPException(status_code=400, detail='Canonical security dimensions cannot be deactivated')
    if payload.code is not None and payload.code != item.code:
        existing = await db.scalar(
            select(SecurityDimensionProfile).where(
                SecurityDimensionProfile.org_id == item.org_id,
                SecurityDimensionProfile.project_id == item.project_id,
                SecurityDimensionProfile.code == payload.code,
                SecurityDimensionProfile.id != item.id,
            )
        )
        if existing is not None:
            raise HTTPException(status_code=400, detail='Security dimension code already exists for project')
        item.code = payload.code
    if payload.name is not None:
        item.name = payload.name
    if payload.description is not None:
        item.description = payload.description
    if payload.order_index is not None:
        item.order_index = payload.order_index
    if payload.is_active is not None:
        item.is_active = payload.is_active
    await db.flush()
    return item


async def delete_dimension_profile(db: AsyncSession, *, item: SecurityDimensionProfile) -> None:
    if is_canonical_dimension_code(item.code):
        raise HTTPException(status_code=400, detail='Canonical security dimensions cannot be deleted')
    await db.delete(item)


async def list_assets(db: AsyncSession, *, org_id: str, project_id: str) -> list[RiskAsset]:
    return (
        await db.execute(
            select(RiskAsset)
            .where(RiskAsset.org_id == org_id, RiskAsset.project_id == project_id)
            .order_by(RiskAsset.created_at.desc())
        )
    ).scalars().all()


async def get_asset(db: AsyncSession, *, org_id: str, project_id: str, asset_id: str) -> RiskAsset:
    item = await db.scalar(
        select(RiskAsset).where(
            RiskAsset.id == asset_id,
            RiskAsset.org_id == org_id,
            RiskAsset.project_id == project_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail='Risk asset not found')
    return item


async def create_asset(db: AsyncSession, *, org_id: str, project_id: str, payload: RiskAssetCreate) -> RiskAsset:
    item = RiskAsset(
        org_id=org_id,
        project_id=project_id,
        name=payload.name,
        asset_type=payload.asset_type,
        owner=payload.owner,
        description=payload.description,
        criticality=payload.criticality,
        metadata_json=payload.metadata_json,
    )
    db.add(item)
    await db.flush()
    return item


async def update_asset(db: AsyncSession, *, item: RiskAsset, payload: RiskAssetUpdate) -> RiskAsset:
    if payload.name is not None:
        item.name = payload.name
    if payload.asset_type is not None:
        item.asset_type = payload.asset_type
    if payload.owner is not None:
        item.owner = payload.owner
    if payload.description is not None:
        item.description = payload.description
    if payload.criticality is not None:
        item.criticality = payload.criticality
    if payload.metadata_json is not None:
        item.metadata_json = payload.metadata_json
    await db.flush()
    return item


async def delete_asset(db: AsyncSession, *, item: RiskAsset) -> None:
    await db.delete(item)


async def _validate_relation_assets(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    source_asset_id: str,
    target_asset_id: str,
) -> None:
    if source_asset_id == target_asset_id:
        raise HTTPException(status_code=400, detail='Asset relation cannot point to the same asset')
    await get_asset(db, org_id=org_id, project_id=project_id, asset_id=source_asset_id)
    await get_asset(db, org_id=org_id, project_id=project_id, asset_id=target_asset_id)


async def list_asset_relations(db: AsyncSession, *, org_id: str, project_id: str) -> list[RiskAssetRelation]:
    return (
        await db.execute(
            select(RiskAssetRelation)
            .where(RiskAssetRelation.org_id == org_id, RiskAssetRelation.project_id == project_id)
            .order_by(RiskAssetRelation.created_at.desc())
        )
    ).scalars().all()


async def get_asset_relation(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    relation_id: str,
) -> RiskAssetRelation:
    item = await db.scalar(
        select(RiskAssetRelation).where(
            RiskAssetRelation.id == relation_id,
            RiskAssetRelation.org_id == org_id,
            RiskAssetRelation.project_id == project_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail='Risk asset relation not found')
    return item


async def create_asset_relation(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    payload: RiskAssetRelationCreate,
) -> RiskAssetRelation:
    await _validate_relation_assets(
        db,
        org_id=org_id,
        project_id=project_id,
        source_asset_id=payload.source_asset_id,
        target_asset_id=payload.target_asset_id,
    )
    item = RiskAssetRelation(
        org_id=org_id,
        project_id=project_id,
        source_asset_id=payload.source_asset_id,
        target_asset_id=payload.target_asset_id,
        relation_type=payload.relation_type,
        description=payload.description,
    )
    db.add(item)
    await db.flush()
    return item


async def update_asset_relation(
    db: AsyncSession,
    *,
    item: RiskAssetRelation,
    payload: RiskAssetRelationUpdate,
) -> RiskAssetRelation:
    source_asset_id = payload.source_asset_id or item.source_asset_id
    target_asset_id = payload.target_asset_id or item.target_asset_id
    if payload.source_asset_id is not None or payload.target_asset_id is not None:
        await _validate_relation_assets(
            db,
            org_id=item.org_id,
            project_id=item.project_id,
            source_asset_id=source_asset_id,
            target_asset_id=target_asset_id,
        )
        item.source_asset_id = source_asset_id
        item.target_asset_id = target_asset_id
    if payload.relation_type is not None:
        item.relation_type = payload.relation_type
    if payload.description is not None:
        item.description = payload.description
    await db.flush()
    return item


async def delete_asset_relation(db: AsyncSession, *, item: RiskAssetRelation) -> None:
    await db.delete(item)


async def list_threats(db: AsyncSession, *, org_id: str, project_id: str) -> list[RiskThreat]:
    return (
        await db.execute(
            select(RiskThreat)
            .where(RiskThreat.org_id == org_id, RiskThreat.project_id == project_id)
            .order_by(RiskThreat.created_at.desc())
        )
    ).scalars().all()


async def get_threat(db: AsyncSession, *, org_id: str, project_id: str, threat_id: str) -> RiskThreat:
    item = await db.scalar(
        select(RiskThreat).where(
            RiskThreat.id == threat_id,
            RiskThreat.org_id == org_id,
            RiskThreat.project_id == project_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail='Risk threat not found')
    return item


async def create_threat(db: AsyncSession, *, org_id: str, project_id: str, payload: RiskThreatCreate) -> RiskThreat:
    item = RiskThreat(
        org_id=org_id,
        project_id=project_id,
        name=payload.name,
        category=payload.category,
        description=payload.description,
        source=payload.source,
    )
    db.add(item)
    await db.flush()
    return item


async def update_threat(db: AsyncSession, *, item: RiskThreat, payload: RiskThreatUpdate) -> RiskThreat:
    if payload.name is not None:
        item.name = payload.name
    if payload.category is not None:
        item.category = payload.category
    if payload.description is not None:
        item.description = payload.description
    if payload.source is not None:
        item.source = payload.source
    await db.flush()
    return item


async def delete_threat(db: AsyncSession, *, item: RiskThreat) -> None:
    await db.delete(item)


async def list_safeguards(db: AsyncSession, *, org_id: str, project_id: str) -> list[RiskSafeguard]:
    return (
        await db.execute(
            select(RiskSafeguard)
            .where(RiskSafeguard.org_id == org_id, RiskSafeguard.project_id == project_id)
            .order_by(RiskSafeguard.created_at.desc())
        )
    ).scalars().all()


async def get_safeguard(db: AsyncSession, *, org_id: str, project_id: str, safeguard_id: str) -> RiskSafeguard:
    item = await db.scalar(
        select(RiskSafeguard).where(
            RiskSafeguard.id == safeguard_id,
            RiskSafeguard.org_id == org_id,
            RiskSafeguard.project_id == project_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail='Risk safeguard not found')
    return item


async def create_safeguard(db: AsyncSession, *, org_id: str, project_id: str, payload: RiskSafeguardCreate) -> RiskSafeguard:
    item = RiskSafeguard(
        org_id=org_id,
        project_id=project_id,
        name=payload.name,
        safeguard_type=payload.safeguard_type,
        description=payload.description,
        status=payload.status,
        reference=payload.reference,
    )
    db.add(item)
    await db.flush()
    return item


async def update_safeguard(db: AsyncSession, *, item: RiskSafeguard, payload: RiskSafeguardUpdate) -> RiskSafeguard:
    if payload.name is not None:
        item.name = payload.name
    if payload.safeguard_type is not None:
        item.safeguard_type = payload.safeguard_type
    if payload.description is not None:
        item.description = payload.description
    if payload.status is not None:
        item.status = payload.status
    if payload.reference is not None:
        item.reference = payload.reference
    await db.flush()
    return item


async def delete_safeguard(db: AsyncSession, *, item: RiskSafeguard) -> None:
    await db.delete(item)


async def list_assessments(db: AsyncSession, *, org_id: str, project_id: str) -> list[RiskAssessment]:
    return (
        await db.execute(
            select(RiskAssessment)
            .where(RiskAssessment.org_id == org_id, RiskAssessment.project_id == project_id)
            .order_by(RiskAssessment.created_at.desc())
        )
    ).scalars().all()


async def get_assessment(db: AsyncSession, *, org_id: str, project_id: str, assessment_id: str) -> RiskAssessment:
    item = await db.scalar(
        select(RiskAssessment).where(
            RiskAssessment.id == assessment_id,
            RiskAssessment.org_id == org_id,
            RiskAssessment.project_id == project_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail='Risk assessment not found')
    return item


async def create_assessment(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    created_by_user_id: str | None,
    payload: RiskAssessmentCreate,
) -> RiskAssessment:
    item = RiskAssessment(
        org_id=org_id,
        project_id=project_id,
        name=payload.name,
        methodology=payload.methodology,
        status=payload.status,
        scope_summary=payload.scope_summary,
        notes=payload.notes,
        assessed_at=payload.assessed_at,
        created_by_user_id=created_by_user_id,
    )
    db.add(item)
    await db.flush()
    return item


async def update_assessment(db: AsyncSession, *, item: RiskAssessment, payload: RiskAssessmentUpdate) -> RiskAssessment:
    if payload.name is not None:
        item.name = payload.name
    if payload.methodology is not None:
        item.methodology = payload.methodology
    if payload.status is not None:
        item.status = payload.status
    if payload.scope_summary is not None:
        item.scope_summary = payload.scope_summary
    if payload.notes is not None:
        item.notes = payload.notes
    if payload.assessed_at is not None:
        item.assessed_at = payload.assessed_at
    await db.flush()
    return item


async def delete_assessment(db: AsyncSession, *, item: RiskAssessment) -> None:
    await db.delete(item)


async def list_scenarios(db: AsyncSession, *, org_id: str, project_id: str) -> list[RiskScenario]:
    return (
        await db.execute(
            select(RiskScenario)
            .where(RiskScenario.org_id == org_id, RiskScenario.project_id == project_id)
            .order_by(RiskScenario.created_at.desc())
        )
    ).scalars().all()


async def get_scenario(db: AsyncSession, *, org_id: str, project_id: str, scenario_id: str) -> RiskScenario:
    item = await db.scalar(
        select(RiskScenario).where(
            RiskScenario.id == scenario_id,
            RiskScenario.org_id == org_id,
            RiskScenario.project_id == project_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail='Risk scenario not found')
    return item


async def _validate_dimension_values(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    dimension_values_json: dict[str, str],
) -> dict[str, str]:
    dimensions = await ensure_default_dimension_profiles(db, org_id=org_id, project_id=project_id, commit=False)
    allowed_codes = {item.code for item in dimensions}
    invalid_codes = sorted(set(dimension_values_json.keys()) - allowed_codes)
    if invalid_codes:
        raise HTTPException(status_code=400, detail=f'Unknown security dimension codes: {", ".join(invalid_codes)}')
    return _normalize_dimension_scale_values(dimension_values_json)


def _normalize_scenario_scale_fields(
    *,
    likelihood: str | None,
    impact: str | None,
) -> tuple[str | None, str | None]:
    return (
        _normalize_formal_scale(likelihood, field_name='likelihood'),
        _normalize_formal_scale(impact, field_name='impact'),
    )


async def _validate_scenario_links(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    assessment_id: str,
    asset_id: str | None,
    threat_id: str | None,
    safeguard_id: str | None,
) -> None:
    await get_assessment(db, org_id=org_id, project_id=project_id, assessment_id=assessment_id)
    if asset_id is not None:
        await get_asset(db, org_id=org_id, project_id=project_id, asset_id=asset_id)
    if threat_id is not None:
        await get_threat(db, org_id=org_id, project_id=project_id, threat_id=threat_id)
    if safeguard_id is not None:
        await get_safeguard(db, org_id=org_id, project_id=project_id, safeguard_id=safeguard_id)


async def create_scenario(db: AsyncSession, *, org_id: str, project_id: str, payload: RiskScenarioCreate) -> RiskScenario:
    await _validate_scenario_links(
        db,
        org_id=org_id,
        project_id=project_id,
        assessment_id=payload.assessment_id,
        asset_id=payload.asset_id,
        threat_id=payload.threat_id,
        safeguard_id=payload.safeguard_id,
    )
    normalized_dimensions = await _validate_dimension_values(
        db,
        org_id=org_id,
        project_id=project_id,
        dimension_values_json=payload.dimension_values_json,
    )
    normalized_likelihood, normalized_impact = _normalize_scenario_scale_fields(
        likelihood=payload.likelihood,
        impact=payload.impact,
    )
    item = RiskScenario(
        org_id=org_id,
        project_id=project_id,
        assessment_id=payload.assessment_id,
        asset_id=payload.asset_id,
        threat_id=payload.threat_id,
        safeguard_id=payload.safeguard_id,
        title=payload.title,
        description=payload.description,
        likelihood=normalized_likelihood,
        impact=normalized_impact,
        risk_level=payload.risk_level,
        dimension_values_json=normalized_dimensions,
        notes=payload.notes,
    )
    db.add(item)
    await db.flush()
    return item


async def update_scenario(db: AsyncSession, *, item: RiskScenario, payload: RiskScenarioUpdate) -> RiskScenario:
    assessment_id = payload.assessment_id or item.assessment_id
    asset_id = payload.asset_id if payload.asset_id is not None else item.asset_id
    threat_id = payload.threat_id if payload.threat_id is not None else item.threat_id
    safeguard_id = payload.safeguard_id if payload.safeguard_id is not None else item.safeguard_id
    if payload.assessment_id is not None or payload.asset_id is not None or payload.threat_id is not None or payload.safeguard_id is not None:
        await _validate_scenario_links(
            db,
            org_id=item.org_id,
            project_id=item.project_id,
            assessment_id=assessment_id,
            asset_id=asset_id,
            threat_id=threat_id,
            safeguard_id=safeguard_id,
        )
        item.assessment_id = assessment_id
        item.asset_id = asset_id
        item.threat_id = threat_id
        item.safeguard_id = safeguard_id
    if payload.title is not None:
        item.title = payload.title
    if payload.description is not None:
        item.description = payload.description
    if payload.likelihood is not None:
        item.likelihood = _normalize_formal_scale(payload.likelihood, field_name='likelihood')
    if payload.impact is not None:
        item.impact = _normalize_formal_scale(payload.impact, field_name='impact')
    if payload.risk_level is not None:
        item.risk_level = payload.risk_level
    if payload.dimension_values_json is not None:
        normalized_dimensions = await _validate_dimension_values(
            db,
            org_id=item.org_id,
            project_id=item.project_id,
            dimension_values_json=payload.dimension_values_json,
        )
        item.dimension_values_json = normalized_dimensions
    if payload.notes is not None:
        item.notes = payload.notes
    await db.flush()
    return item


async def delete_scenario(db: AsyncSession, *, item: RiskScenario) -> None:
    await db.delete(item)


async def list_treatments(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    scenario_id: str,
) -> list[RiskTreatmentDecision]:
    return (
        await db.execute(
            select(RiskTreatmentDecision)
            .where(
                RiskTreatmentDecision.org_id == org_id,
                RiskTreatmentDecision.project_id == project_id,
                RiskTreatmentDecision.scenario_id == scenario_id,
            )
            .order_by(RiskTreatmentDecision.created_at.desc())
        )
    ).scalars().all()


async def get_treatment(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    scenario_id: str,
    treatment_id: str,
) -> RiskTreatmentDecision:
    item = await db.scalar(
        select(RiskTreatmentDecision).where(
            RiskTreatmentDecision.id == treatment_id,
            RiskTreatmentDecision.org_id == org_id,
            RiskTreatmentDecision.project_id == project_id,
            RiskTreatmentDecision.scenario_id == scenario_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail='Risk treatment decision not found')
    return item


async def create_treatment(
    db: AsyncSession,
    *,
    scenario: RiskScenario,
    decided_by_user_id: str | None,
    payload: RiskTreatmentDecisionCreate,
) -> RiskTreatmentDecision:
    await _validate_owner_user_membership(db, org_id=scenario.org_id, owner_user_id=payload.owner_user_id)
    if payload.safeguard_id is not None:
        await get_safeguard(
            db,
            org_id=scenario.org_id,
            project_id=scenario.project_id,
            safeguard_id=payload.safeguard_id,
        )
    normalized = _normalize_treatment_fields(
        decision=payload.decision,
        status=payload.status,
        applies_to=payload.applies_to,
        effectiveness_pct=payload.effectiveness_pct,
    )
    item = RiskTreatmentDecision(
        org_id=scenario.org_id,
        project_id=scenario.project_id,
        assessment_id=scenario.assessment_id,
        scenario_id=scenario.id,
        safeguard_id=payload.safeguard_id,
        title=payload.title,
        decision=normalized['decision'],
        status=normalized['status'],
        applies_to=normalized['applies_to'],
        effectiveness_pct=normalized['effectiveness_pct'],
        rationale=payload.rationale,
        implementation_notes=payload.implementation_notes,
        owner_user_id=payload.owner_user_id,
        decided_by_user_id=decided_by_user_id,
        due_date=payload.due_date,
        review_due_at=payload.review_due_at,
        metadata_json=payload.metadata_json,
    )
    db.add(item)
    await db.flush()
    return item


async def update_treatment(
    db: AsyncSession,
    *,
    item: RiskTreatmentDecision,
    decided_by_user_id: str | None,
    payload: RiskTreatmentDecisionUpdate,
) -> RiskTreatmentDecision:
    owner_user_id = item.owner_user_id if payload.owner_user_id is None else payload.owner_user_id
    await _validate_owner_user_membership(db, org_id=item.org_id, owner_user_id=owner_user_id)
    safeguard_id = item.safeguard_id if payload.safeguard_id is None else payload.safeguard_id
    if safeguard_id is not None:
        await get_safeguard(
            db,
            org_id=item.org_id,
            project_id=item.project_id,
            safeguard_id=safeguard_id,
        )
    normalized = _normalize_treatment_fields(
        decision=payload.decision or item.decision,
        status=payload.status or item.status,
        applies_to=payload.applies_to or item.applies_to,
        effectiveness_pct=payload.effectiveness_pct if payload.effectiveness_pct is not None else item.effectiveness_pct,
    )

    item.safeguard_id = safeguard_id
    if payload.title is not None:
        item.title = payload.title
    item.decision = normalized['decision']
    item.status = normalized['status']
    item.applies_to = normalized['applies_to']
    item.effectiveness_pct = normalized['effectiveness_pct']
    if payload.rationale is not None:
        item.rationale = payload.rationale
    if payload.implementation_notes is not None:
        item.implementation_notes = payload.implementation_notes
    if payload.owner_user_id is not None:
        item.owner_user_id = payload.owner_user_id
    if payload.due_date is not None:
        item.due_date = payload.due_date
    if payload.review_due_at is not None:
        item.review_due_at = payload.review_due_at
    if payload.metadata_json is not None:
        item.metadata_json = payload.metadata_json
    item.decided_by_user_id = decided_by_user_id
    await db.flush()
    return item


async def delete_treatment(db: AsyncSession, *, item: RiskTreatmentDecision) -> None:
    await db.delete(item)


async def list_scenario_evaluations(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    scenario_id: str,
) -> list[RiskScenarioEvaluation]:
    return (
        await db.execute(
            select(RiskScenarioEvaluation)
            .where(
                RiskScenarioEvaluation.org_id == org_id,
                RiskScenarioEvaluation.project_id == project_id,
                RiskScenarioEvaluation.scenario_id == scenario_id,
            )
            .order_by(RiskScenarioEvaluation.version.desc(), RiskScenarioEvaluation.created_at.desc())
        )
    ).scalars().all()


async def get_scenario_evaluation(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    scenario_id: str,
    evaluation_id: str,
) -> RiskScenarioEvaluation:
    item = await db.scalar(
        select(RiskScenarioEvaluation).where(
            RiskScenarioEvaluation.id == evaluation_id,
            RiskScenarioEvaluation.org_id == org_id,
            RiskScenarioEvaluation.project_id == project_id,
            RiskScenarioEvaluation.scenario_id == scenario_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail='Risk scenario evaluation not found')
    return item


async def create_scenario_evaluation(
    db: AsyncSession,
    *,
    scenario: RiskScenario,
    created_by_user_id: str | None,
    payload: RiskScenarioEvaluationCreate,
) -> RiskScenarioEvaluation:
    asset = None
    threat = None
    safeguard = None
    if scenario.asset_id is not None:
        asset_row = await get_asset(db, org_id=scenario.org_id, project_id=scenario.project_id, asset_id=scenario.asset_id)
        asset = risk_asset_to_dict(asset_row)
    if scenario.threat_id is not None:
        threat_row = await get_threat(
            db,
            org_id=scenario.org_id,
            project_id=scenario.project_id,
            threat_id=scenario.threat_id,
        )
        threat = risk_threat_to_dict(threat_row)
    if scenario.safeguard_id is not None:
        safeguard_row = await get_safeguard(
            db,
            org_id=scenario.org_id,
            project_id=scenario.project_id,
            safeguard_id=scenario.safeguard_id,
        )
        safeguard = risk_safeguard_to_dict(safeguard_row)

    treatments = await list_treatments(
        db,
        org_id=scenario.org_id,
        project_id=scenario.project_id,
        scenario_id=scenario.id,
    )
    if payload.treatment_ids:
        treatment_index = {item.id: item for item in treatments}
        missing = sorted(set(payload.treatment_ids) - set(treatment_index))
        if missing:
            raise HTTPException(status_code=400, detail=f'Unknown treatment ids for scenario: {", ".join(missing)}')
        selected_treatments = [treatment_index[item_id] for item_id in payload.treatment_ids]
    else:
        selected_treatments = treatments

    try:
        result = evaluate_scenario(
            scenario_id=scenario.id,
            likelihood=scenario.likelihood,
            impact=scenario.impact,
            dimension_values=scenario.dimension_values_json,
            asset=asset,
            threat=threat,
            safeguard=safeguard,
            treatments=[
                TreatmentInput(
                    id=item.id,
                    title=item.title,
                    decision=item.decision,
                    status=item.status,
                    applies_to=item.applies_to,
                    effectiveness_pct=item.effectiveness_pct,
                    safeguard_id=item.safeguard_id,
                )
                for item in selected_treatments
            ],
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await _lock_scenario_for_evaluation(db, scenario=scenario)

    for attempt in range(3):
        nested = await db.begin_nested()
        try:
            next_version = int(
                await db.scalar(
                    select(func.coalesce(func.max(RiskScenarioEvaluation.version), 0)).where(
                        RiskScenarioEvaluation.scenario_id == scenario.id
                    )
                )
                or 0
            ) + 1

            item = RiskScenarioEvaluation(
                org_id=scenario.org_id,
                project_id=scenario.project_id,
                assessment_id=scenario.assessment_id,
                scenario_id=scenario.id,
                version=next_version,
                engine_version=result['engine_version'],
                inherent_likelihood=result['inherent_likelihood'],
                inherent_impact=result['inherent_impact'],
                inherent_score=result['inherent_score'],
                inherent_level=result['inherent_level'],
                residual_likelihood=result['residual_likelihood'],
                residual_impact=result['residual_impact'],
                residual_score=result['residual_score'],
                residual_level=result['residual_level'],
                input_snapshot_json=result['input_snapshot_json'],
                trace_json=result['trace_json'],
                notes=payload.notes,
                created_by_user_id=created_by_user_id,
            )
            db.add(item)
            await _flush_risk_scenario_evaluation_insert(db)
        except IntegrityError as exc:
            await nested.rollback()
            if _is_scenario_evaluation_version_conflict(exc) and attempt < 2:
                continue
            if _is_scenario_evaluation_version_conflict(exc):
                raise HTTPException(status_code=409, detail='Concurrent risk scenario evaluation conflict, retry request') from exc
            raise
        else:
            await nested.commit()
            return item

    raise HTTPException(status_code=409, detail='Concurrent risk scenario evaluation conflict, retry request')


async def get_risk_register(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
) -> list[dict[str, Any]]:
    scenarios = await list_scenarios(db, org_id=org_id, project_id=project_id)
    if not scenarios:
        return []

    scenario_ids = [item.id for item in scenarios]
    treatments = (
        await db.execute(
            select(RiskTreatmentDecision)
            .where(
                RiskTreatmentDecision.org_id == org_id,
                RiskTreatmentDecision.project_id == project_id,
                RiskTreatmentDecision.scenario_id.in_(scenario_ids),
            )
            .order_by(RiskTreatmentDecision.created_at.desc())
        )
    ).scalars().all()
    evaluations = (
        await db.execute(
            select(RiskScenarioEvaluation)
            .where(
                RiskScenarioEvaluation.org_id == org_id,
                RiskScenarioEvaluation.project_id == project_id,
                RiskScenarioEvaluation.scenario_id.in_(scenario_ids),
            )
            .order_by(RiskScenarioEvaluation.version.desc(), RiskScenarioEvaluation.created_at.desc())
        )
    ).scalars().all()

    treatments_by_scenario: dict[str, list[RiskTreatmentDecision]] = {}
    for item in treatments:
        treatments_by_scenario.setdefault(item.scenario_id, []).append(item)

    latest_evaluation_by_scenario: dict[str, RiskScenarioEvaluation] = {}
    evaluation_count_by_scenario: dict[str, int] = {}
    for item in evaluations:
        latest_evaluation_by_scenario.setdefault(item.scenario_id, item)
        evaluation_count_by_scenario[item.scenario_id] = evaluation_count_by_scenario.get(item.scenario_id, 0) + 1

    register = []
    for scenario in scenarios:
        scenario_treatments = treatments_by_scenario.get(scenario.id, [])
        latest = latest_evaluation_by_scenario.get(scenario.id)
        register.append(
            {
                'scenario': risk_scenario_to_dict(scenario),
                'latest_evaluation': risk_scenario_evaluation_to_dict(latest) if latest else None,
                'treatments': [risk_treatment_decision_to_dict(item) for item in scenario_treatments],
                'traceability': {
                    'evaluation_versions': evaluation_count_by_scenario.get(scenario.id, 0),
                    'treatments_total': len(scenario_treatments),
                    'implemented_treatments': len([item for item in scenario_treatments if item.status == 'implemented']),
                    'accepted_treatments': len(
                        [item for item in scenario_treatments if item.decision == 'accept' and item.status == 'accepted']
                    ),
                    'last_evaluated_at': latest.created_at.isoformat() if latest else None,
                },
            }
        )
    return register


async def get_scenario_traceability(
    db: AsyncSession,
    *,
    org_id: str,
    project_id: str,
    scenario: RiskScenario,
) -> dict[str, Any]:
    assessment = await get_assessment(
        db,
        org_id=org_id,
        project_id=project_id,
        assessment_id=scenario.assessment_id,
    )
    asset = None
    threat = None
    safeguard = None
    if scenario.asset_id is not None:
        asset = risk_asset_to_dict(await get_asset(db, org_id=org_id, project_id=project_id, asset_id=scenario.asset_id))
    if scenario.threat_id is not None:
        threat = risk_threat_to_dict(await get_threat(db, org_id=org_id, project_id=project_id, threat_id=scenario.threat_id))
    if scenario.safeguard_id is not None:
        safeguard = risk_safeguard_to_dict(
            await get_safeguard(db, org_id=org_id, project_id=project_id, safeguard_id=scenario.safeguard_id)
        )

    treatments = await list_treatments(db, org_id=org_id, project_id=project_id, scenario_id=scenario.id)
    evaluations = await list_scenario_evaluations(db, org_id=org_id, project_id=project_id, scenario_id=scenario.id)

    audit_rows = (
        await db.execute(
            select(AuditLogEntry)
            .where(
                AuditLogEntry.org_id == org_id,
                AuditLogEntry.action.like('risk.%'),
            )
            .order_by(AuditLogEntry.created_at.desc())
        )
    ).scalars().all()
    relevant_entity_types = {'risk_scenario', 'risk_treatment_decision', 'risk_scenario_evaluation'}
    filtered_logs = [
        item
        for item in audit_rows
        if item.entity_type in relevant_entity_types and _audit_log_matches_scenario(item, scenario_id=scenario.id)
    ]

    return {
        'scenario': risk_scenario_to_dict(scenario),
        'assessment': risk_assessment_to_dict(assessment),
        'asset': asset,
        'threat': threat,
        'safeguard': safeguard,
        'evaluations': [risk_scenario_evaluation_to_dict(item) for item in evaluations],
        'latest_evaluation': risk_scenario_evaluation_to_dict(evaluations[0]) if evaluations else None,
        'treatments': [risk_treatment_decision_to_dict(item) for item in treatments],
        'audit_log': [audit_log_entry_to_dict(item) for item in filtered_logs],
    }


async def get_risk_overview(db: AsyncSession, *, org_id: str, project_id: str) -> dict[str, Any]:
    dimensions = await list_dimension_profiles(db, org_id=org_id, project_id=project_id, ensure_defaults=False)
    assets = await list_assets(db, org_id=org_id, project_id=project_id)
    asset_relations = await list_asset_relations(db, org_id=org_id, project_id=project_id)
    threats = await list_threats(db, org_id=org_id, project_id=project_id)
    safeguards = await list_safeguards(db, org_id=org_id, project_id=project_id)
    assessments = await list_assessments(db, org_id=org_id, project_id=project_id)
    scenarios = await list_scenarios(db, org_id=org_id, project_id=project_id)
    register = await get_risk_register(db, org_id=org_id, project_id=project_id)
    return {
        'dimensions': [security_dimension_profile_to_dict(item) for item in dimensions],
        'assets': [risk_asset_to_dict(item) for item in assets],
        'asset_relations': [risk_asset_relation_to_dict(item) for item in asset_relations],
        'threats': [risk_threat_to_dict(item) for item in threats],
        'safeguards': [risk_safeguard_to_dict(item) for item in safeguards],
        'assessments': [risk_assessment_to_dict(item) for item in assessments],
        'scenarios': [risk_scenario_to_dict(item) for item in scenarios],
        'risk_register': register,
    }
