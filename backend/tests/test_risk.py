from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select

from app import main as main_module
from app.db import SessionLocal
from app.models import Membership, Organization, Project, RoleEnum, User
from app.risk.models import RISK_TABLE_NAMES, SecurityDimensionProfile
from app.risk import service as risk_service
from app.risk.schemas import RiskScenarioEvaluationCreate
from app.risk.service import ensure_default_dimension_profiles


def _login(client, email: str, org_id: str) -> str:
    response = client.post('/auth/mock/login', json={'email': email, 'org_id': org_id})
    assert response.status_code == 200, response.text
    return response.json()['access_token']


def test_risk_overview_seeds_default_dimensions(client, seeded_ids):
    token = _login(client, seeded_ids['users']['viewer'], seeded_ids['org_id'])

    response = client.get(
        f"/projects/{seeded_ids['project_id']}/risk",
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert [item['code'] for item in payload['dimensions']] == ['C', 'I', 'A', 'AUT', 'TRAZ']
    assert payload['assets'] == []
    assert payload['asset_relations'] == []
    assert payload['threats'] == []
    assert payload['safeguards'] == []
    assert payload['assessments'] == []
    assert payload['scenarios'] == []


def test_risk_get_endpoints_have_no_side_effects(client, seeded_ids):
    token = _login(client, seeded_ids['users']['viewer'], seeded_ids['org_id'])
    headers = {'Authorization': f'Bearer {token}'}

    async def _seed_uninitialized_project() -> tuple[str, int]:
        async with SessionLocal() as db:
            project = Project(
                org_id=seeded_ids['org_id'],
                name='Uninitialized Risk Project',
                description='No seeded dimensions',
            )
            db.add(project)
            await db.flush()
            before = int(
                await db.scalar(
                    select(func.count())
                    .select_from(SecurityDimensionProfile)
                    .where(SecurityDimensionProfile.project_id == project.id)
                )
                or 0
            )
            await db.commit()
            return project.id, before

    project_id, before_count = asyncio.run(_seed_uninitialized_project())
    assert before_count == 0

    overview = client.get(f'/projects/{project_id}/risk', headers=headers)
    dimensions = client.get(f'/projects/{project_id}/risk/dimensions', headers=headers)
    assert overview.status_code == 200, overview.text
    assert dimensions.status_code == 200, dimensions.text
    assert overview.json()['dimensions'] == []
    assert dimensions.json() == []

    async def _count_dimensions() -> int:
        async with SessionLocal() as db:
            return int(
                await db.scalar(
                    select(func.count())
                    .select_from(SecurityDimensionProfile)
                    .where(SecurityDimensionProfile.project_id == project_id)
                )
                or 0
            )

    assert asyncio.run(_count_dimensions()) == 0


def test_dimension_seed_repairs_partial_set():
    async def _run() -> list[str]:
        async with SessionLocal() as db:
            org = Organization(name='Risk Partial Seed Org')
            db.add(org)
            await db.flush()
            project = Project(org_id=org.id, name='Partial Risk Seed')
            db.add(project)
            await db.flush()
            db.add(
                SecurityDimensionProfile(
                    org_id=org.id,
                    project_id=project.id,
                    code='C',
                    name='Confidencialidad',
                    description='Existing canonical row',
                    order_index=0,
                    is_active=True,
                )
            )
            await db.commit()

        async with SessionLocal() as db:
            rows = await ensure_default_dimension_profiles(db, org_id=org.id, project_id=project.id, commit=True)
            return [row.code for row in rows]

    assert asyncio.run(_run()) == ['C', 'I', 'A', 'AUT', 'TRAZ']


def test_dimension_seed_is_idempotent_under_reasonable_concurrency():
    async def _run() -> tuple[list[str], int]:
        async with SessionLocal() as db:
            org = Organization(name='Risk Concurrency Org')
            db.add(org)
            await db.flush()
            project = Project(org_id=org.id, name='Concurrent Risk Seed')
            db.add(project)
            await db.flush()
            project_id = project.id
            org_id = org.id
            await db.commit()

        async def _worker() -> None:
            async with SessionLocal() as db:
                await ensure_default_dimension_profiles(db, org_id=org_id, project_id=project_id, commit=True)

        await asyncio.gather(_worker(), _worker())

        async with SessionLocal() as db:
            rows = (
                await db.execute(
                    select(SecurityDimensionProfile)
                    .where(SecurityDimensionProfile.project_id == project_id)
                    .order_by(SecurityDimensionProfile.order_index.asc(), SecurityDimensionProfile.code.asc())
                )
            ).scalars().all()
            return [row.code for row in rows], len(rows)

    codes, total = asyncio.run(_run())
    assert codes == ['C', 'I', 'A', 'AUT', 'TRAZ']
    assert total == 5


def test_canonical_dimensions_cannot_be_deleted(client, seeded_ids):
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'])
    headers = {'Authorization': f'Bearer {token}'}

    dimensions = client.get(f"/projects/{seeded_ids['project_id']}/risk/dimensions", headers=headers)
    assert dimensions.status_code == 200, dimensions.text
    dimension_id = next(item['id'] for item in dimensions.json() if item['code'] == 'C')

    response = client.delete(
        f"/projects/{seeded_ids['project_id']}/risk/dimensions/{dimension_id}",
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()['detail'] == 'Canonical security dimensions cannot be deleted'


def test_auto_create_schema_bootstrap_excludes_risk_tables():
    bootstrap_names = set(main_module._bootstrap_schema_table_names())
    assert bootstrap_names
    assert bootstrap_names.isdisjoint(RISK_TABLE_NAMES)


def test_risk_crud_happy_path(client, seeded_ids):
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'])
    headers = {'Authorization': f'Bearer {token}'}
    project_id = seeded_ids['project_id']

    asset_a = client.post(
        f'/projects/{project_id}/risk/assets',
        json={'name': 'ERP', 'asset_type': 'application', 'criticality': 'high'},
        headers=headers,
    )
    assert asset_a.status_code == 200, asset_a.text

    asset_b = client.post(
        f'/projects/{project_id}/risk/assets',
        json={'name': 'Customer DB', 'asset_type': 'database', 'criticality': 'high'},
        headers=headers,
    )
    assert asset_b.status_code == 200, asset_b.text

    relation = client.post(
        f'/projects/{project_id}/risk/asset-relations',
        json={
            'source_asset_id': asset_a.json()['id'],
            'target_asset_id': asset_b.json()['id'],
            'relation_type': 'stores',
        },
        headers=headers,
    )
    assert relation.status_code == 200, relation.text

    threat = client.post(
        f'/projects/{project_id}/risk/threats',
        json={'name': 'Ransomware', 'category': 'malware'},
        headers=headers,
    )
    assert threat.status_code == 200, threat.text

    safeguard = client.post(
        f'/projects/{project_id}/risk/safeguards',
        json={'name': 'Immutable backups', 'safeguard_type': 'technical', 'status': 'implemented'},
        headers=headers,
    )
    assert safeguard.status_code == 200, safeguard.text

    assessment = client.post(
        f'/projects/{project_id}/risk/assessments',
        json={'name': '2026 Baseline', 'methodology': 'manual-v1', 'status': 'draft'},
        headers=headers,
    )
    assert assessment.status_code == 200, assessment.text

    scenario = client.post(
        f'/projects/{project_id}/risk/scenarios',
        json={
            'assessment_id': assessment.json()['id'],
            'asset_id': asset_b.json()['id'],
            'threat_id': threat.json()['id'],
            'safeguard_id': safeguard.json()['id'],
            'title': 'Database unavailable by ransomware',
            'likelihood': 'medium',
            'impact': 'high',
            'risk_level': 'high',
            'dimension_values_json': {'C': 'high', 'I': 'high', 'A': 'very_high'},
        },
        headers=headers,
    )
    assert scenario.status_code == 200, scenario.text

    updated_asset = client.patch(
        f"/projects/{project_id}/risk/assets/{asset_a.json()['id']}",
        json={'owner': 'IT Ops', 'metadata_json': {'cmdb_id': 'CMDB-1'}},
        headers=headers,
    )
    assert updated_asset.status_code == 200, updated_asset.text
    assert updated_asset.json()['owner'] == 'IT Ops'

    updated_assessment = client.patch(
        f"/projects/{project_id}/risk/assessments/{assessment.json()['id']}",
        json={'status': 'in_review'},
        headers=headers,
    )
    assert updated_assessment.status_code == 200, updated_assessment.text
    assert updated_assessment.json()['status'] == 'in_review'

    updated_scenario = client.patch(
        f"/projects/{project_id}/risk/scenarios/{scenario.json()['id']}",
        json={'notes': 'Manual formal assessment only'},
        headers=headers,
    )
    assert updated_scenario.status_code == 200, updated_scenario.text
    assert updated_scenario.json()['notes'] == 'Manual formal assessment only'

    overview = client.get(f'/projects/{project_id}/risk', headers=headers)
    assert overview.status_code == 200, overview.text
    payload = overview.json()
    assert len(payload['dimensions']) == 5
    assert len(payload['assets']) == 2
    assert len(payload['asset_relations']) == 1
    assert len(payload['threats']) == 1
    assert len(payload['safeguards']) == 1
    assert len(payload['assessments']) == 1
    assert len(payload['scenarios']) == 1

    delete_relation = client.delete(
        f"/projects/{project_id}/risk/asset-relations/{relation.json()['id']}",
        headers=headers,
    )
    assert delete_relation.status_code == 204, delete_relation.text

    delete_scenario = client.delete(
        f"/projects/{project_id}/risk/scenarios/{scenario.json()['id']}",
        headers=headers,
    )
    assert delete_scenario.status_code == 204, delete_scenario.text


def test_risk_scenario_rejects_unknown_dimension_code(client, seeded_ids):
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'])
    headers = {'Authorization': f'Bearer {token}'}
    project_id = seeded_ids['project_id']

    assessment = client.post(
        f'/projects/{project_id}/risk/assessments',
        json={'name': 'Invalid dimensions', 'methodology': 'manual-v1'},
        headers=headers,
    )
    assert assessment.status_code == 200, assessment.text

    response = client.post(
        f'/projects/{project_id}/risk/scenarios',
        json={
            'assessment_id': assessment.json()['id'],
            'title': 'Bad dimension payload',
            'dimension_values_json': {'XYZ': 'high'},
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert 'Unknown security dimension codes' in response.json()['detail']


def test_risk_rbac_blocks_viewer_writes(client, seeded_ids):
    token = _login(client, seeded_ids['users']['viewer'], seeded_ids['org_id'])
    headers = {'Authorization': f'Bearer {token}'}
    project_id = seeded_ids['project_id']

    read_response = client.get(f'/projects/{project_id}/risk', headers=headers)
    assert read_response.status_code == 200, read_response.text

    write_response = client.post(
        f'/projects/{project_id}/risk/assets',
        json={'name': 'Blocked asset'},
        headers=headers,
    )

    assert write_response.status_code == 403


def test_risk_deterministic_engine_treatments_and_traceability(client, seeded_ids):
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'])
    headers = {'Authorization': f'Bearer {token}'}
    project_id = seeded_ids['project_id']

    asset = client.post(
        f'/projects/{project_id}/risk/assets',
        json={'name': 'Customer DB', 'asset_type': 'database', 'criticality': 'high'},
        headers=headers,
    )
    assert asset.status_code == 200, asset.text

    threat = client.post(
        f'/projects/{project_id}/risk/threats',
        json={'name': 'Ransomware', 'category': 'malware'},
        headers=headers,
    )
    assert threat.status_code == 200, threat.text

    safeguard = client.post(
        f'/projects/{project_id}/risk/safeguards',
        json={'name': 'Immutable backups', 'safeguard_type': 'technical', 'status': 'implemented'},
        headers=headers,
    )
    assert safeguard.status_code == 200, safeguard.text

    assessment = client.post(
        f'/projects/{project_id}/risk/assessments',
        json={'name': '2026 Formal Register', 'methodology': 'manual-v1', 'status': 'draft'},
        headers=headers,
    )
    assert assessment.status_code == 200, assessment.text

    scenario = client.post(
        f'/projects/{project_id}/risk/scenarios',
        json={
            'assessment_id': assessment.json()['id'],
            'asset_id': asset.json()['id'],
            'threat_id': threat.json()['id'],
            'safeguard_id': safeguard.json()['id'],
            'title': 'Customer DB encrypted by ransomware',
            'likelihood': 'high',
            'dimension_values_json': {'C': 'high', 'I': 'very_high', 'A': 'very_high'},
        },
        headers=headers,
    )
    assert scenario.status_code == 200, scenario.text
    scenario_id = scenario.json()['id']

    treatment = client.post(
        f'/projects/{project_id}/risk/scenarios/{scenario_id}/treatments',
        json={
            'title': 'Deploy immutable offline backups',
            'decision': 'mitigate',
            'status': 'implemented',
            'applies_to': 'impact',
            'effectiveness_pct': 60,
            'safeguard_id': safeguard.json()['id'],
        },
        headers=headers,
    )
    assert treatment.status_code == 200, treatment.text

    first_evaluation = client.post(
        f'/projects/{project_id}/risk/scenarios/{scenario_id}/evaluations',
        json={},
        headers=headers,
    )
    assert first_evaluation.status_code == 200, first_evaluation.text
    first_payload = first_evaluation.json()
    assert first_payload['version'] == 1
    assert first_payload['engine_version'] == 'deterministic-v1'
    assert first_payload['inherent_score'] == 20.0
    assert first_payload['inherent_level'] == 'critical'
    assert first_payload['residual_score'] == 8.0
    assert first_payload['residual_level'] == 'medium'
    assert first_payload['trace_json']['treatments']['selected'][0]['id'] == treatment.json()['id']

    updated_treatment = client.patch(
        f"/projects/{project_id}/risk/scenarios/{scenario_id}/treatments/{treatment.json()['id']}",
        json={'status': 'accepted', 'decision': 'accept'},
        headers=headers,
    )
    assert updated_treatment.status_code == 200, updated_treatment.text
    assert updated_treatment.json()['decision'] == 'accept'
    assert updated_treatment.json()['effectiveness_pct'] == 0
    assert updated_treatment.json()['applies_to'] == 'none'

    second_evaluation = client.post(
        f'/projects/{project_id}/risk/scenarios/{scenario_id}/evaluations',
        json={},
        headers=headers,
    )
    assert second_evaluation.status_code == 200, second_evaluation.text
    second_payload = second_evaluation.json()
    assert second_payload['version'] == 2
    assert second_payload['residual_score'] == 20.0
    assert second_payload['residual_level'] == 'critical'
    assert second_payload['trace_json']['treatments']['accepted_ids'] == [treatment.json()['id']]

    evaluations = client.get(
        f'/projects/{project_id}/risk/scenarios/{scenario_id}/evaluations',
        headers=headers,
    )
    assert evaluations.status_code == 200, evaluations.text
    assert [item['version'] for item in evaluations.json()] == [2, 1]

    register = client.get(f'/projects/{project_id}/risk/register', headers=headers)
    assert register.status_code == 200, register.text
    assert register.json()[0]['latest_evaluation']['version'] == 2
    assert register.json()[0]['traceability']['evaluation_versions'] == 2
    assert register.json()[0]['traceability']['accepted_treatments'] == 1

    traceability = client.get(
        f'/projects/{project_id}/risk/scenarios/{scenario_id}/traceability',
        headers=headers,
    )
    assert traceability.status_code == 200, traceability.text
    trace_payload = traceability.json()
    assert trace_payload['latest_evaluation']['version'] == 2
    assert len(trace_payload['treatments']) == 1
    assert len(trace_payload['evaluations']) == 2
    assert {item['action'] for item in trace_payload['audit_log']} >= {
        'risk.treatment.create',
        'risk.treatment.update',
        'risk.scenario.evaluate',
    }


def test_risk_deterministic_engine_requires_formal_inputs(client, seeded_ids):
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'])
    headers = {'Authorization': f'Bearer {token}'}
    project_id = seeded_ids['project_id']

    assessment = client.post(
        f'/projects/{project_id}/risk/assessments',
        json={'name': 'Missing likelihood', 'methodology': 'manual-v1'},
        headers=headers,
    )
    assert assessment.status_code == 200, assessment.text

    scenario = client.post(
        f'/projects/{project_id}/risk/scenarios',
        json={
            'assessment_id': assessment.json()['id'],
            'title': 'Scenario without formal scales',
            'dimension_values_json': {'C': 'high'},
        },
        headers=headers,
    )
    assert scenario.status_code == 200, scenario.text

    evaluation = client.post(
        f"/projects/{project_id}/risk/scenarios/{scenario.json()['id']}/evaluations",
        json={},
        headers=headers,
    )

    assert evaluation.status_code == 400
    assert 'likelihood is required' in evaluation.json()['detail']


def test_risk_scenario_rejects_invalid_formal_scales_on_create_and_update(client, seeded_ids):
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'])
    headers = {'Authorization': f'Bearer {token}'}
    project_id = seeded_ids['project_id']

    assessment = client.post(
        f'/projects/{project_id}/risk/assessments',
        json={'name': 'Formal scales', 'methodology': 'manual-v1'},
        headers=headers,
    )
    assert assessment.status_code == 200, assessment.text

    invalid_likelihood = client.post(
        f'/projects/{project_id}/risk/scenarios',
        json={
            'assessment_id': assessment.json()['id'],
            'title': 'Invalid likelihood',
            'likelihood': 'impossible',
        },
        headers=headers,
    )
    assert invalid_likelihood.status_code == 400
    assert 'Unsupported likelihood value' in invalid_likelihood.json()['detail']

    invalid_dimension_value = client.post(
        f'/projects/{project_id}/risk/scenarios',
        json={
            'assessment_id': assessment.json()['id'],
            'title': 'Invalid dimension value',
            'likelihood': 'high',
            'dimension_values_json': {'C': 'catastrophic'},
        },
        headers=headers,
    )
    assert invalid_dimension_value.status_code == 400
    assert 'Unsupported dimension C value' in invalid_dimension_value.json()['detail']

    scenario = client.post(
        f'/projects/{project_id}/risk/scenarios',
        json={
            'assessment_id': assessment.json()['id'],
            'title': 'Valid scenario',
            'likelihood': 'alto',
            'impact': 'medio',
        },
        headers=headers,
    )
    assert scenario.status_code == 200, scenario.text
    assert scenario.json()['likelihood'] == 'high'
    assert scenario.json()['impact'] == 'medium'

    invalid_update = client.patch(
        f"/projects/{project_id}/risk/scenarios/{scenario.json()['id']}",
        json={'impact': 'catastrophic'},
        headers=headers,
    )
    assert invalid_update.status_code == 400
    assert 'Unsupported impact value' in invalid_update.json()['detail']


def test_risk_treatment_owner_must_belong_to_same_org(client, seeded_ids):
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'])
    headers = {'Authorization': f'Bearer {token}'}
    project_id = seeded_ids['project_id']

    async def _seed_external_owner() -> str:
        async with SessionLocal() as db:
            other_org = Organization(name='Other Owner Org')
            external_user = User(email='external-owner@test.local', display_name='External Owner')
            db.add_all([other_org, external_user])
            await db.flush()
            db.add(Membership(org_id=other_org.id, user_id=external_user.id, role=RoleEnum.auditor))
            await db.commit()
            return external_user.id

    external_owner_id = asyncio.run(_seed_external_owner())

    assessment = client.post(
        f'/projects/{project_id}/risk/assessments',
        json={'name': 'Treatment owner assessment', 'methodology': 'manual-v1'},
        headers=headers,
    )
    assert assessment.status_code == 200, assessment.text

    scenario = client.post(
        f'/projects/{project_id}/risk/scenarios',
        json={
            'assessment_id': assessment.json()['id'],
            'title': 'Cross-tenant owner scenario',
            'likelihood': 'high',
            'impact': 'high',
        },
        headers=headers,
    )
    assert scenario.status_code == 200, scenario.text

    response = client.post(
        f"/projects/{project_id}/risk/scenarios/{scenario.json()['id']}/treatments",
        json={
            'title': 'Bad owner assignment',
            'decision': 'mitigate',
            'status': 'proposed',
            'owner_user_id': external_owner_id,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()['detail'] == 'owner_user_id must belong to the same organization'


def test_risk_traceability_keeps_delete_events(client, seeded_ids):
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'])
    headers = {'Authorization': f'Bearer {token}'}
    project_id = seeded_ids['project_id']

    assessment = client.post(
        f'/projects/{project_id}/risk/assessments',
        json={'name': 'Traceability delete', 'methodology': 'manual-v1'},
        headers=headers,
    )
    assert assessment.status_code == 200, assessment.text

    scenario = client.post(
        f'/projects/{project_id}/risk/scenarios',
        json={
            'assessment_id': assessment.json()['id'],
            'title': 'Delete treatment traceability',
            'likelihood': 'high',
            'impact': 'high',
        },
        headers=headers,
    )
    assert scenario.status_code == 200, scenario.text

    treatment = client.post(
        f"/projects/{project_id}/risk/scenarios/{scenario.json()['id']}/treatments",
        json={'title': 'Temporary treatment', 'decision': 'mitigate', 'status': 'proposed'},
        headers=headers,
    )
    assert treatment.status_code == 200, treatment.text

    deleted = client.delete(
        f"/projects/{project_id}/risk/scenarios/{scenario.json()['id']}/treatments/{treatment.json()['id']}",
        headers=headers,
    )
    assert deleted.status_code == 204, deleted.text

    traceability = client.get(
        f"/projects/{project_id}/risk/scenarios/{scenario.json()['id']}/traceability",
        headers=headers,
    )
    assert traceability.status_code == 200, traceability.text
    payload = traceability.json()
    assert payload['treatments'] == []
    assert {item['action'] for item in payload['audit_log']} >= {'risk.treatment.create', 'risk.treatment.delete'}


def test_risk_scenario_evaluation_retries_on_version_conflict(monkeypatch):
    async def _run() -> tuple[int, int]:
        async with SessionLocal() as db:
            org = Organization(name='Risk Retry Org')
            user = User(email='retry@test.local', display_name='Retry User')
            db.add_all([org, user])
            await db.flush()
            db.add(Membership(org_id=org.id, user_id=user.id, role=RoleEnum.auditor))
            project = Project(org_id=org.id, name='Retry Project')
            db.add(project)
            await db.flush()
            assessment = await risk_service.create_assessment(
                db,
                org_id=org.id,
                project_id=project.id,
                created_by_user_id=user.id,
                payload=risk_service.RiskAssessmentCreate(name='Retry Assessment'),
            )
            scenario = await risk_service.create_scenario(
                db,
                org_id=org.id,
                project_id=project.id,
                payload=risk_service.RiskScenarioCreate(
                    assessment_id=assessment.id,
                    title='Retry Scenario',
                    likelihood='high',
                    impact='high',
                ),
            )
            await db.commit()

        attempts = {'count': 0}
        original_flush = risk_service._flush_risk_scenario_evaluation_insert

        async def _flaky_flush(db):
            attempts['count'] += 1
            if attempts['count'] == 1:
                raise IntegrityError(
                    'INSERT',
                    {},
                    Exception('UNIQUE constraint failed: risk_scenario_evaluations.scenario_id, risk_scenario_evaluations.version'),
                )
            await original_flush(db)

        monkeypatch.setattr(risk_service, '_flush_risk_scenario_evaluation_insert', _flaky_flush)
        try:
            async with SessionLocal() as db:
                scenario = await risk_service.get_scenario(db, org_id=org.id, project_id=project.id, scenario_id=scenario.id)
                evaluation = await risk_service.create_scenario_evaluation(
                    db,
                    scenario=scenario,
                    created_by_user_id=user.id,
                    payload=RiskScenarioEvaluationCreate(),
                )
                await db.commit()
                return evaluation.version, attempts['count']
        finally:
            monkeypatch.setattr(risk_service, '_flush_risk_scenario_evaluation_insert', original_flush)

    version, attempts = asyncio.run(_run())
    assert version == 1
    assert attempts == 2


def test_risk_scenario_evaluation_returns_409_after_repeated_version_conflict(monkeypatch):
    async def _run() -> str:
        async with SessionLocal() as db:
            org = Organization(name='Risk Conflict Org')
            user = User(email='conflict@test.local', display_name='Conflict User')
            db.add_all([org, user])
            await db.flush()
            db.add(Membership(org_id=org.id, user_id=user.id, role=RoleEnum.auditor))
            project = Project(org_id=org.id, name='Conflict Project')
            db.add(project)
            await db.flush()
            assessment = await risk_service.create_assessment(
                db,
                org_id=org.id,
                project_id=project.id,
                created_by_user_id=user.id,
                payload=risk_service.RiskAssessmentCreate(name='Conflict Assessment'),
            )
            scenario = await risk_service.create_scenario(
                db,
                org_id=org.id,
                project_id=project.id,
                payload=risk_service.RiskScenarioCreate(
                    assessment_id=assessment.id,
                    title='Conflict Scenario',
                    likelihood='high',
                    impact='high',
                ),
            )
            await db.commit()

        original_flush = risk_service._flush_risk_scenario_evaluation_insert

        async def _always_conflict(_db):
            raise IntegrityError(
                'INSERT',
                {},
                Exception('UNIQUE constraint failed: risk_scenario_evaluations.scenario_id, risk_scenario_evaluations.version'),
            )

        monkeypatch.setattr(risk_service, '_flush_risk_scenario_evaluation_insert', _always_conflict)
        try:
            async with SessionLocal() as db:
                scenario = await risk_service.get_scenario(db, org_id=org.id, project_id=project.id, scenario_id=scenario.id)
                with pytest.raises(HTTPException) as exc_info:
                    await risk_service.create_scenario_evaluation(
                        db,
                        scenario=scenario,
                        created_by_user_id=user.id,
                        payload=RiskScenarioEvaluationCreate(),
                    )
                return str(exc_info.value.detail)
        finally:
            monkeypatch.setattr(risk_service, '_flush_risk_scenario_evaluation_insert', original_flush)

    message = asyncio.run(_run())
    assert 'Concurrent risk scenario evaluation conflict' in message
