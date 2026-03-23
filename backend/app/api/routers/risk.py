from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit_log import append_audit_log
from app.db import get_db
from app.deps import UserContext, get_current_user, require_roles
from app.permissions import require_permission
from app.risk import service
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

router = APIRouter(tags=['Risk'])


async def _project_with_permission(
    db: AsyncSession,
    *,
    ctx: UserContext,
    project_id: str,
    action: str,
    ensure_seed: bool = False,
) -> None:
    project = await service.get_project_for_org(db, org_id=ctx.org_id, project_id=project_id)
    await require_permission(db, org_id=ctx.org_id, role=ctx.role, resource='project', action=action, project=project)
    if ensure_seed:
        await service.ensure_default_dimension_profiles(db, org_id=ctx.org_id, project_id=project_id, commit=False)


@router.get('/projects/{project_id}/risk')
async def get_risk_overview(
    project_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='read')
    return await service.get_risk_overview(db, org_id=ctx.org_id, project_id=project_id)


@router.get('/projects/{project_id}/risk/register')
async def get_risk_register(
    project_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='read')
    return await service.get_risk_register(db, org_id=ctx.org_id, project_id=project_id)


@router.get('/projects/{project_id}/risk/dimensions')
async def list_dimension_profiles(
    project_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='read')
    rows = await service.list_dimension_profiles(db, org_id=ctx.org_id, project_id=project_id, ensure_defaults=False)
    return [service.security_dimension_profile_to_dict(row) for row in rows]


@router.post('/projects/{project_id}/risk/dimensions')
async def create_dimension_profile(
    project_id: str,
    payload: SecurityDimensionProfileCreate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.create_dimension_profile(db, org_id=ctx.org_id, project_id=project_id, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.dimension.create',
        entity_type='security_dimension_profile',
        entity_id=row.id,
        payload={'project_id': project_id, 'code': row.code},
    )
    await db.commit()
    return service.security_dimension_profile_to_dict(row)


@router.patch('/projects/{project_id}/risk/dimensions/{dimension_id}')
async def update_dimension_profile(
    project_id: str,
    dimension_id: str,
    payload: SecurityDimensionProfileUpdate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.get_dimension_profile(db, org_id=ctx.org_id, project_id=project_id, dimension_id=dimension_id)
    row = await service.update_dimension_profile(db, item=row, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.dimension.update',
        entity_type='security_dimension_profile',
        entity_id=row.id,
        payload=payload.model_dump(exclude_none=True),
    )
    await db.commit()
    return service.security_dimension_profile_to_dict(row)


@router.delete('/projects/{project_id}/risk/dimensions/{dimension_id}', status_code=204)
async def delete_dimension_profile(
    project_id: str,
    dimension_id: str,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.get_dimension_profile(db, org_id=ctx.org_id, project_id=project_id, dimension_id=dimension_id)
    await service.delete_dimension_profile(db, item=row)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.dimension.delete',
        entity_type='security_dimension_profile',
        entity_id=dimension_id,
        payload={'project_id': project_id},
    )
    await db.commit()
    return Response(status_code=204)


@router.get('/projects/{project_id}/risk/assets')
async def list_assets(
    project_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='read')
    rows = await service.list_assets(db, org_id=ctx.org_id, project_id=project_id)
    return [service.risk_asset_to_dict(row) for row in rows]


@router.post('/projects/{project_id}/risk/assets')
async def create_asset(
    project_id: str,
    payload: RiskAssetCreate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.create_asset(db, org_id=ctx.org_id, project_id=project_id, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.asset.create',
        entity_type='risk_asset',
        entity_id=row.id,
        payload={'project_id': project_id, 'name': row.name},
    )
    await db.commit()
    return service.risk_asset_to_dict(row)


@router.patch('/projects/{project_id}/risk/assets/{asset_id}')
async def update_asset(
    project_id: str,
    asset_id: str,
    payload: RiskAssetUpdate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.get_asset(db, org_id=ctx.org_id, project_id=project_id, asset_id=asset_id)
    row = await service.update_asset(db, item=row, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.asset.update',
        entity_type='risk_asset',
        entity_id=row.id,
        payload=payload.model_dump(exclude_none=True),
    )
    await db.commit()
    return service.risk_asset_to_dict(row)


@router.delete('/projects/{project_id}/risk/assets/{asset_id}', status_code=204)
async def delete_asset(
    project_id: str,
    asset_id: str,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.get_asset(db, org_id=ctx.org_id, project_id=project_id, asset_id=asset_id)
    await service.delete_asset(db, item=row)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.asset.delete',
        entity_type='risk_asset',
        entity_id=asset_id,
        payload={'project_id': project_id},
    )
    await db.commit()
    return Response(status_code=204)


@router.get('/projects/{project_id}/risk/asset-relations')
async def list_asset_relations(
    project_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='read')
    rows = await service.list_asset_relations(db, org_id=ctx.org_id, project_id=project_id)
    return [service.risk_asset_relation_to_dict(row) for row in rows]


@router.post('/projects/{project_id}/risk/asset-relations')
async def create_asset_relation(
    project_id: str,
    payload: RiskAssetRelationCreate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.create_asset_relation(db, org_id=ctx.org_id, project_id=project_id, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.asset_relation.create',
        entity_type='risk_asset_relation',
        entity_id=row.id,
        payload={'project_id': project_id, 'relation_type': row.relation_type},
    )
    await db.commit()
    return service.risk_asset_relation_to_dict(row)


@router.patch('/projects/{project_id}/risk/asset-relations/{relation_id}')
async def update_asset_relation(
    project_id: str,
    relation_id: str,
    payload: RiskAssetRelationUpdate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.get_asset_relation(db, org_id=ctx.org_id, project_id=project_id, relation_id=relation_id)
    row = await service.update_asset_relation(db, item=row, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.asset_relation.update',
        entity_type='risk_asset_relation',
        entity_id=row.id,
        payload=payload.model_dump(exclude_none=True),
    )
    await db.commit()
    return service.risk_asset_relation_to_dict(row)


@router.delete('/projects/{project_id}/risk/asset-relations/{relation_id}', status_code=204)
async def delete_asset_relation(
    project_id: str,
    relation_id: str,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.get_asset_relation(db, org_id=ctx.org_id, project_id=project_id, relation_id=relation_id)
    await service.delete_asset_relation(db, item=row)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.asset_relation.delete',
        entity_type='risk_asset_relation',
        entity_id=relation_id,
        payload={'project_id': project_id},
    )
    await db.commit()
    return Response(status_code=204)


@router.get('/projects/{project_id}/risk/threats')
async def list_threats(
    project_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='read')
    rows = await service.list_threats(db, org_id=ctx.org_id, project_id=project_id)
    return [service.risk_threat_to_dict(row) for row in rows]


@router.post('/projects/{project_id}/risk/threats')
async def create_threat(
    project_id: str,
    payload: RiskThreatCreate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.create_threat(db, org_id=ctx.org_id, project_id=project_id, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.threat.create',
        entity_type='risk_threat',
        entity_id=row.id,
        payload={'project_id': project_id, 'name': row.name},
    )
    await db.commit()
    return service.risk_threat_to_dict(row)


@router.patch('/projects/{project_id}/risk/threats/{threat_id}')
async def update_threat(
    project_id: str,
    threat_id: str,
    payload: RiskThreatUpdate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.get_threat(db, org_id=ctx.org_id, project_id=project_id, threat_id=threat_id)
    row = await service.update_threat(db, item=row, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.threat.update',
        entity_type='risk_threat',
        entity_id=row.id,
        payload=payload.model_dump(exclude_none=True),
    )
    await db.commit()
    return service.risk_threat_to_dict(row)


@router.delete('/projects/{project_id}/risk/threats/{threat_id}', status_code=204)
async def delete_threat(
    project_id: str,
    threat_id: str,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.get_threat(db, org_id=ctx.org_id, project_id=project_id, threat_id=threat_id)
    await service.delete_threat(db, item=row)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.threat.delete',
        entity_type='risk_threat',
        entity_id=threat_id,
        payload={'project_id': project_id},
    )
    await db.commit()
    return Response(status_code=204)


@router.get('/projects/{project_id}/risk/safeguards')
async def list_safeguards(
    project_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='read')
    rows = await service.list_safeguards(db, org_id=ctx.org_id, project_id=project_id)
    return [service.risk_safeguard_to_dict(row) for row in rows]


@router.post('/projects/{project_id}/risk/safeguards')
async def create_safeguard(
    project_id: str,
    payload: RiskSafeguardCreate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.create_safeguard(db, org_id=ctx.org_id, project_id=project_id, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.safeguard.create',
        entity_type='risk_safeguard',
        entity_id=row.id,
        payload={'project_id': project_id, 'name': row.name},
    )
    await db.commit()
    return service.risk_safeguard_to_dict(row)


@router.patch('/projects/{project_id}/risk/safeguards/{safeguard_id}')
async def update_safeguard(
    project_id: str,
    safeguard_id: str,
    payload: RiskSafeguardUpdate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.get_safeguard(db, org_id=ctx.org_id, project_id=project_id, safeguard_id=safeguard_id)
    row = await service.update_safeguard(db, item=row, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.safeguard.update',
        entity_type='risk_safeguard',
        entity_id=row.id,
        payload=payload.model_dump(exclude_none=True),
    )
    await db.commit()
    return service.risk_safeguard_to_dict(row)


@router.delete('/projects/{project_id}/risk/safeguards/{safeguard_id}', status_code=204)
async def delete_safeguard(
    project_id: str,
    safeguard_id: str,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.get_safeguard(db, org_id=ctx.org_id, project_id=project_id, safeguard_id=safeguard_id)
    await service.delete_safeguard(db, item=row)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.safeguard.delete',
        entity_type='risk_safeguard',
        entity_id=safeguard_id,
        payload={'project_id': project_id},
    )
    await db.commit()
    return Response(status_code=204)


@router.get('/projects/{project_id}/risk/assessments')
async def list_assessments(
    project_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='read')
    rows = await service.list_assessments(db, org_id=ctx.org_id, project_id=project_id)
    return [service.risk_assessment_to_dict(row) for row in rows]


@router.post('/projects/{project_id}/risk/assessments')
async def create_assessment(
    project_id: str,
    payload: RiskAssessmentCreate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.create_assessment(
        db,
        org_id=ctx.org_id,
        project_id=project_id,
        created_by_user_id=ctx.user_id,
        payload=payload,
    )
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.assessment.create',
        entity_type='risk_assessment',
        entity_id=row.id,
        payload={'project_id': project_id, 'name': row.name},
    )
    await db.commit()
    return service.risk_assessment_to_dict(row)


@router.patch('/projects/{project_id}/risk/assessments/{assessment_id}')
async def update_assessment(
    project_id: str,
    assessment_id: str,
    payload: RiskAssessmentUpdate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.get_assessment(db, org_id=ctx.org_id, project_id=project_id, assessment_id=assessment_id)
    row = await service.update_assessment(db, item=row, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.assessment.update',
        entity_type='risk_assessment',
        entity_id=row.id,
        payload=payload.model_dump(exclude_none=True),
    )
    await db.commit()
    return service.risk_assessment_to_dict(row)


@router.delete('/projects/{project_id}/risk/assessments/{assessment_id}', status_code=204)
async def delete_assessment(
    project_id: str,
    assessment_id: str,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write', ensure_seed=True)
    row = await service.get_assessment(db, org_id=ctx.org_id, project_id=project_id, assessment_id=assessment_id)
    await service.delete_assessment(db, item=row)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.assessment.delete',
        entity_type='risk_assessment',
        entity_id=assessment_id,
        payload={'project_id': project_id},
    )
    await db.commit()
    return Response(status_code=204)


@router.get('/projects/{project_id}/risk/scenarios')
async def list_scenarios(
    project_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='read')
    rows = await service.list_scenarios(db, org_id=ctx.org_id, project_id=project_id)
    return [service.risk_scenario_to_dict(row) for row in rows]


@router.post('/projects/{project_id}/risk/scenarios')
async def create_scenario(
    project_id: str,
    payload: RiskScenarioCreate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write')
    row = await service.create_scenario(db, org_id=ctx.org_id, project_id=project_id, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.scenario.create',
        entity_type='risk_scenario',
        entity_id=row.id,
        payload={'project_id': project_id, 'title': row.title},
    )
    await db.commit()
    return service.risk_scenario_to_dict(row)


@router.patch('/projects/{project_id}/risk/scenarios/{scenario_id}')
async def update_scenario(
    project_id: str,
    scenario_id: str,
    payload: RiskScenarioUpdate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write')
    row = await service.get_scenario(db, org_id=ctx.org_id, project_id=project_id, scenario_id=scenario_id)
    row = await service.update_scenario(db, item=row, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.scenario.update',
        entity_type='risk_scenario',
        entity_id=row.id,
        payload=payload.model_dump(exclude_none=True),
    )
    await db.commit()
    return service.risk_scenario_to_dict(row)


@router.delete('/projects/{project_id}/risk/scenarios/{scenario_id}', status_code=204)
async def delete_scenario(
    project_id: str,
    scenario_id: str,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write')
    row = await service.get_scenario(db, org_id=ctx.org_id, project_id=project_id, scenario_id=scenario_id)
    await service.delete_scenario(db, item=row)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.scenario.delete',
        entity_type='risk_scenario',
        entity_id=scenario_id,
        payload={'project_id': project_id},
    )
    await db.commit()
    return Response(status_code=204)


@router.get('/projects/{project_id}/risk/scenarios/{scenario_id}/evaluations')
async def list_scenario_evaluations(
    project_id: str,
    scenario_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='read')
    await service.get_scenario(db, org_id=ctx.org_id, project_id=project_id, scenario_id=scenario_id)
    rows = await service.list_scenario_evaluations(db, org_id=ctx.org_id, project_id=project_id, scenario_id=scenario_id)
    return [service.risk_scenario_evaluation_to_dict(row) for row in rows]


@router.post('/projects/{project_id}/risk/scenarios/{scenario_id}/evaluations')
async def create_scenario_evaluation(
    project_id: str,
    scenario_id: str,
    payload: RiskScenarioEvaluationCreate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write')
    scenario = await service.get_scenario(db, org_id=ctx.org_id, project_id=project_id, scenario_id=scenario_id)
    row = await service.create_scenario_evaluation(
        db,
        scenario=scenario,
        created_by_user_id=ctx.user_id,
        payload=payload,
    )
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.scenario.evaluate',
        entity_type='risk_scenario_evaluation',
        entity_id=row.id,
        payload={
            'project_id': project_id,
            'scenario_id': scenario_id,
            'version': row.version,
            'engine_version': row.engine_version,
            'residual_level': row.residual_level,
            'residual_score': row.residual_score,
        },
    )
    await db.commit()
    return service.risk_scenario_evaluation_to_dict(row)


@router.get('/projects/{project_id}/risk/scenarios/{scenario_id}/evaluations/{evaluation_id}')
async def get_scenario_evaluation(
    project_id: str,
    scenario_id: str,
    evaluation_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='read')
    row = await service.get_scenario_evaluation(
        db,
        org_id=ctx.org_id,
        project_id=project_id,
        scenario_id=scenario_id,
        evaluation_id=evaluation_id,
    )
    return service.risk_scenario_evaluation_to_dict(row)


@router.get('/projects/{project_id}/risk/scenarios/{scenario_id}/treatments')
async def list_treatments(
    project_id: str,
    scenario_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='read')
    await service.get_scenario(db, org_id=ctx.org_id, project_id=project_id, scenario_id=scenario_id)
    rows = await service.list_treatments(db, org_id=ctx.org_id, project_id=project_id, scenario_id=scenario_id)
    return [service.risk_treatment_decision_to_dict(row) for row in rows]


@router.post('/projects/{project_id}/risk/scenarios/{scenario_id}/treatments')
async def create_treatment(
    project_id: str,
    scenario_id: str,
    payload: RiskTreatmentDecisionCreate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write')
    scenario = await service.get_scenario(db, org_id=ctx.org_id, project_id=project_id, scenario_id=scenario_id)
    row = await service.create_treatment(db, scenario=scenario, decided_by_user_id=ctx.user_id, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.treatment.create',
        entity_type='risk_treatment_decision',
        entity_id=row.id,
        payload={'project_id': project_id, 'scenario_id': scenario_id, 'decision': row.decision, 'status': row.status},
    )
    await db.commit()
    return service.risk_treatment_decision_to_dict(row)


@router.patch('/projects/{project_id}/risk/scenarios/{scenario_id}/treatments/{treatment_id}')
async def update_treatment(
    project_id: str,
    scenario_id: str,
    treatment_id: str,
    payload: RiskTreatmentDecisionUpdate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write')
    row = await service.get_treatment(
        db,
        org_id=ctx.org_id,
        project_id=project_id,
        scenario_id=scenario_id,
        treatment_id=treatment_id,
    )
    row = await service.update_treatment(db, item=row, decided_by_user_id=ctx.user_id, payload=payload)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.treatment.update',
        entity_type='risk_treatment_decision',
        entity_id=row.id,
        payload={'project_id': project_id, 'scenario_id': scenario_id, **payload.model_dump(exclude_none=True)},
    )
    await db.commit()
    return service.risk_treatment_decision_to_dict(row)


@router.delete('/projects/{project_id}/risk/scenarios/{scenario_id}/treatments/{treatment_id}', status_code=204)
async def delete_treatment(
    project_id: str,
    scenario_id: str,
    treatment_id: str,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='write')
    row = await service.get_treatment(
        db,
        org_id=ctx.org_id,
        project_id=project_id,
        scenario_id=scenario_id,
        treatment_id=treatment_id,
    )
    await service.delete_treatment(db, item=row)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='risk.treatment.delete',
        entity_type='risk_treatment_decision',
        entity_id=treatment_id,
        payload={'project_id': project_id, 'scenario_id': scenario_id},
    )
    await db.commit()
    return Response(status_code=204)


@router.get('/projects/{project_id}/risk/scenarios/{scenario_id}/traceability')
async def get_scenario_traceability(
    project_id: str,
    scenario_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_with_permission(db, ctx=ctx, project_id=project_id, action='read')
    scenario = await service.get_scenario(db, org_id=ctx.org_id, project_id=project_id, scenario_id=scenario_id)
    return await service.get_scenario_traceability(db, org_id=ctx.org_id, project_id=project_id, scenario=scenario)
