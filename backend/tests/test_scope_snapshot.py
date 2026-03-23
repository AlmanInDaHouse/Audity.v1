from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from app import main as main_module
from app.catalog_engine import build_catalog_snapshot, load_controls, load_controls_from_snapshot
from app.db import SessionLocal
from app.schemas import ProjectCreate
from app.temporal_workflow import AuditRunWorkflowInput
from app.workflow_runtime import AuditWorkflowInput, evaluate_controls_activity


def _login(client, email: str, org_id: str, *, mfa: bool = False) -> str:
    response = client.post('/auth/mock/login', json={'email': email, 'org_id': org_id, 'mfa': mfa})
    assert response.status_code == 200, response.text
    return response.json()['access_token']


def test_project_schema_normalizes_frameworks():
    payload = ProjectCreate(name='Scope Test', frameworks=['ENS', 'ENS', 'ISO27001'])
    assert payload.frameworks == ['ENS', 'ISO27001']


def test_project_schema_rejects_invalid_framework():
    with pytest.raises(ValidationError):
        ProjectCreate(name='Scope Test', frameworks=['NIST'])


def test_catalog_snapshot_filters_controls_by_framework():
    snapshot = build_catalog_snapshot(['RGPD'])
    assert snapshot['frameworks'] == ['RGPD']
    assert len(snapshot['checksum']) == 64
    assert snapshot['controls']
    assert all(item['framework'] == 'RGPD' for item in snapshot['controls'])


def test_project_frameworks_persist_and_run_snapshot_is_immutable(client, seeded_ids, monkeypatch):
    async def _noop_launch(_payload: AuditRunWorkflowInput) -> None:
        return None

    monkeypatch.setattr(main_module, 'launch_audit_workflow', _noop_launch)
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'], mfa=True)
    headers = {'Authorization': f'Bearer {token}'}

    create_project = client.post(
        f"/organizations/{seeded_ids['org_id']}/projects",
        json={
            'name': 'Scoped project',
            'description': 'Only ISO initially',
            'criticality': 'medium',
            'frameworks': ['ISO27001'],
        },
        headers=headers,
    )
    assert create_project.status_code == 200, create_project.text
    project_id = create_project.json()['id']

    create_run = client.post(
        f"/projects/{project_id}/audit-runs",
        json={'catalog_version': 'v1'},
        headers=headers,
    )
    assert create_run.status_code == 200, create_run.text
    run_payload = create_run.json()
    assert run_payload['frameworks_json'] == ['ISO27001']
    assert len(run_payload['catalog_checksum']) == 64

    update_project = client.patch(
        f"/projects/{project_id}",
        json={'frameworks': ['ENS']},
        headers=headers,
    )
    assert update_project.status_code == 200, update_project.text
    assert update_project.json()['frameworks'] == ['ENS']

    get_run = client.get(
        f"/projects/{project_id}/audit-runs/{run_payload['id']}",
        headers=headers,
    )
    assert get_run.status_code == 200, get_run.text
    assert get_run.json()['frameworks_json'] == ['ISO27001']

    async def _assert_json_lists() -> None:
        async with SessionLocal() as db:
            from app.models import AuditRun, Project

            project = await db.get(Project, project_id)
            run = await db.get(AuditRun, run_payload['id'])
            assert isinstance(project.frameworks_json, list)
            assert project.frameworks_json == ['ENS']
            assert isinstance(run.frameworks_json, list)
            assert run.frameworks_json == ['ISO27001']

    asyncio.run(_assert_json_lists())


def test_runtime_uses_run_snapshot_scope(client, seeded_ids, monkeypatch):
    async def _noop_launch(_payload: AuditRunWorkflowInput) -> None:
        return None

    monkeypatch.setattr(main_module, 'launch_audit_workflow', _noop_launch)
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'], mfa=True)
    headers = {'Authorization': f'Bearer {token}'}

    create_project = client.post(
        f"/organizations/{seeded_ids['org_id']}/projects",
        json={
            'name': 'RGPD project',
            'description': 'Snapshot scoped run',
            'criticality': 'medium',
            'frameworks': ['RGPD'],
        },
        headers=headers,
    )
    assert create_project.status_code == 200, create_project.text
    project_id = create_project.json()['id']

    create_run = client.post(
        f"/projects/{project_id}/audit-runs",
        json={'catalog_version': 'v1'},
        headers=headers,
    )
    assert create_run.status_code == 200, create_run.text
    run_payload = create_run.json()

    control_eval = asyncio.run(
        evaluate_controls_activity(
            AuditWorkflowInput(
                org_id=seeded_ids['org_id'],
                project_id=project_id,
                audit_run_id=run_payload['id'],
                actor_user_id='system',
                catalog_version='v1',
            ),
            {'github': {}, 'google_workspace': {}, 'manual': [], 'ai_assessment': {'assessments': []}},
        )
    )

    expected_controls = [item for item in load_controls() if item.framework == 'RGPD']
    assert control_eval['total_controls'] == len(expected_controls)
    assert all(item['framework'] == 'RGPD' for item in control_eval['results'])


def test_load_controls_from_invalid_snapshot_raises() -> None:
    with pytest.raises(ValueError, match='controls must be a list'):
        load_controls_from_snapshot({'controls': 'broken'})


def test_runtime_rejects_invalid_snapshot_instead_of_falling_back(client, seeded_ids, monkeypatch):
    async def _noop_launch(_payload: AuditRunWorkflowInput) -> None:
        return None

    monkeypatch.setattr(main_module, 'launch_audit_workflow', _noop_launch)
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'], mfa=True)
    headers = {'Authorization': f'Bearer {token}'}

    create_run = client.post(
        f"/projects/{seeded_ids['project_id']}/audit-runs",
        json={'catalog_version': 'v1'},
        headers=headers,
    )
    assert create_run.status_code == 200, create_run.text
    run_id = create_run.json()['id']

    async def _corrupt_snapshot() -> None:
        async with SessionLocal() as db:
            from app.models import AuditRun

            run = await db.get(AuditRun, run_id)
            assert run is not None
            run.catalog_snapshot_json = {'controls': 'broken'}
            await db.commit()

    asyncio.run(_corrupt_snapshot())

    with pytest.raises(ValueError, match='controls must be a list'):
        asyncio.run(
            evaluate_controls_activity(
                AuditWorkflowInput(
                    org_id=seeded_ids['org_id'],
                    project_id=seeded_ids['project_id'],
                    audit_run_id=run_id,
                    actor_user_id='system',
                    catalog_version='v1',
                ),
                {'github': {}, 'google_workspace': {}, 'manual': [], 'ai_assessment': {'assessments': []}},
            )
        )


def test_pricing_plan_accepts_max_projects_and_keeps_max_assets_alias(client, seeded_ids):
    token = _login(client, seeded_ids['users']['admin'], seeded_ids['org_id'])
    headers = {'Authorization': f'Bearer {token}'}

    update_response = client.put(
        f"/organizations/{seeded_ids['org_id']}/pricing-plan",
        json={
            'plan_code': 'growth',
            'max_projects': 7,
            'max_upload_bytes': 10 * 1024 * 1024,
            'modules_json': {'reporting_package': True},
        },
        headers=headers,
    )
    assert update_response.status_code == 200, update_response.text
    payload = update_response.json()
    assert payload['max_projects'] == 7
    assert payload['max_assets'] == 7

    get_response = client.get(
        f"/organizations/{seeded_ids['org_id']}/pricing-plan",
        headers=headers,
    )
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()['max_projects'] == 7
    assert get_response.json()['max_assets'] == 7
