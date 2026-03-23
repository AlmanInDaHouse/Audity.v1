from __future__ import annotations

import asyncio

from app import main as main_module
from app.catalog_engine import build_catalog_bundle
from app.db import SessionLocal
from app.temporal_workflow import AuditRunWorkflowInput


def _login(client, email: str, org_id: str, *, mfa: bool = False) -> str:
    response = client.post('/auth/mock/login', json={'email': email, 'org_id': org_id, 'mfa': mfa})
    assert response.status_code == 200, response.text
    return response.json()['access_token']


def test_list_catalog_versions_includes_seeded_core_catalog(client, seeded_ids):
    token = _login(client, seeded_ids['users']['admin'], seeded_ids['org_id'])
    response = client.get('/catalog-versions', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200, response.text
    rows = response.json()
    assert any(
        row['name'] == 'core-catalog' and row['version'] == 'v1' and row['status'] == 'published'
        for row in rows
    )


def test_create_catalog_version_rejects_unknown_evaluator_key(client, seeded_ids):
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'])
    response = client.post(
        '/catalog-versions',
        json={
            'name': 'core-catalog',
            'version': 'v2',
            'frameworks': ['ISO27001'],
            'bundle_json': {
                'version': 'v2',
                'frameworks': ['ISO27001'],
                'controls': [
                    {
                        'id': 'ISO-A.5.1',
                        'framework': 'ISO27001',
                        'title': 'Policy',
                        'description': 'Policy exists',
                        'severity': 'medium',
                        'mapped_controls': [],
                        'evidence_requirements': ['policy'],
                        'evaluator_key': 'does_not_exist',
                        'tags': ['policy'],
                        'level': 'base',
                    }
                ],
                'control_mapping': {'ISO-A.5.1': ['REQ-1']},
            },
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 400, response.text
    assert 'Unknown evaluator_key' in response.json()['detail']


def test_new_run_uses_persisted_catalog_bundle_not_live_disk(client, seeded_ids, monkeypatch):
    async def _noop_launch(_payload: AuditRunWorkflowInput) -> None:
        return None

    monkeypatch.setattr(main_module, 'launch_audit_workflow', _noop_launch)

    token = _login(client, seeded_ids['users']['admin'], seeded_ids['org_id'], mfa=True)
    headers = {'Authorization': f'Bearer {token}'}
    bundle = build_catalog_bundle(['RGPD'], version='v2')

    create_catalog = client.post(
        '/catalog-versions',
        json={
            'name': 'core-catalog',
            'version': 'v2',
            'frameworks': ['RGPD'],
            'bundle_json': bundle,
        },
        headers=headers,
    )
    assert create_catalog.status_code == 200, create_catalog.text
    catalog_version = create_catalog.json()

    publish_catalog = client.post(
        f"/catalog-versions/{catalog_version['id']}/publish",
        headers=headers,
    )
    assert publish_catalog.status_code == 200, publish_catalog.text
    published = publish_catalog.json()

    def _boom(*_args, **_kwargs):
        raise AssertionError('live disk controls should not be loaded for published catalog-backed runs')

    monkeypatch.setattr('app.catalog_engine.load_controls', _boom)

    create_project = client.post(
        f"/organizations/{seeded_ids['org_id']}/projects",
        json={
            'name': 'Published catalog project',
            'description': 'Uses persisted bundle',
            'criticality': 'medium',
            'frameworks': ['RGPD'],
        },
        headers=headers,
    )
    assert create_project.status_code == 200, create_project.text
    project_id = create_project.json()['id']

    create_run = client.post(
        f"/projects/{project_id}/audit-runs",
        json={'catalog_version': 'v2'},
        headers=headers,
    )
    assert create_run.status_code == 200, create_run.text
    run_payload = create_run.json()
    assert run_payload['catalog_version_id'] == published['id']
    assert run_payload['catalog_checksum'] == published['checksum']
    assert run_payload['frameworks_json'] == ['RGPD']

    async def _assert_snapshot() -> None:
        async with SessionLocal() as db:
            from app.models import AuditRun

            run = await db.get(AuditRun, run_payload['id'])
            assert run is not None
            assert run.catalog_version_id == published['id']
            assert run.catalog_snapshot_json is not None
            assert run.catalog_snapshot_json['checksum'] == published['checksum']
            assert all(item['framework'] == 'RGPD' for item in run.catalog_snapshot_json['controls'])

    asyncio.run(_assert_snapshot())
