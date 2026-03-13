from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from app.audit_log import append_audit_log
from app.db import SessionLocal
from app.models import (
    AuditRun,
    AuditStatusEnum,
    EvidenceItem,
    Finding,
    FindingStatusEnum,
    Integration,
    OutboundIntegration,
    PricingPlan,
    RemediationTask,
    SeverityEnum,
)


def _login(client, email: str, org_id: str) -> str:
    response = client.post('/auth/mock/login', json={'email': email, 'org_id': org_id, 'mfa': True})
    assert response.status_code == 200, response.text
    return response.json()['access_token']


def test_dashboard_summary_returns_market_kpis(client, seeded_ids):
    async def _seed() -> None:
        async with SessionLocal() as db:
            db.add(
                PricingPlan(
                    org_id=seeded_ids['org_id'],
                    plan_code='growth',
                    max_assets=4,
                    max_upload_bytes=50 * 1024 * 1024,
                    modules_json={'approvals': True, 'reporting_package': True},
                )
            )
            db.add(
                Integration(
                    org_id=seeded_ids['org_id'],
                    project_id=seeded_ids['project_id'],
                    provider='github',
                    name='GitHub',
                    config_json={'repos': ['acme/app']},
                    secret_ref='secret://github/token',
                    is_enabled=True,
                )
            )
            db.add(
                OutboundIntegration(
                    org_id=seeded_ids['org_id'],
                    kind='siem',
                    name='SIEM',
                    config_json={'endpoint': 'https://example.test'},
                    is_enabled=True,
                )
            )
            run = AuditRun(
                org_id=seeded_ids['org_id'],
                project_id=seeded_ids['project_id'],
                triggered_by_user_id=None,
                status=AuditStatusEnum.completed,
                catalog_version='v1',
                progress_json={'stage': 'completed'},
                summary_json={'controls': 12},
                risk_score=72.5,
                risk_level='high',
            )
            db.add(run)
            await db.flush()

            db.add_all(
                [
                    EvidenceItem(
                        org_id=seeded_ids['org_id'],
                        project_id=seeded_ids['project_id'],
                        audit_run_id=run.id,
                        integration_id=None,
                        item_type='manual_upload',
                        name='clean.txt',
                        object_key='memory://clean.txt',
                        sha256='a' * 64,
                        metadata_json={'content_type': 'text/plain'},
                        scan_status='clean',
                    ),
                    EvidenceItem(
                        org_id=seeded_ids['org_id'],
                        project_id=seeded_ids['project_id'],
                        audit_run_id=run.id,
                        integration_id=None,
                        item_type='manual_upload',
                        name='quarantine.txt',
                        object_key='memory://quarantine.txt',
                        sha256='b' * 64,
                        metadata_json={'content_type': 'text/plain'},
                        scan_status='infected',
                        quarantine_reason='av_scan_infected',
                    ),
                ]
            )
            finding = Finding(
                org_id=seeded_ids['org_id'],
                project_id=seeded_ids['project_id'],
                audit_run_id=run.id,
                control_id='A.5.1',
                title='Critical gap',
                severity=SeverityEnum.high,
                result='fail',
                confidence=0.97,
                notes='Test finding',
                status=FindingStatusEnum.open,
                evidence_refs_json=[],
            )
            db.add(finding)
            db.add(
                RemediationTask(
                    org_id=seeded_ids['org_id'],
                    project_id=seeded_ids['project_id'],
                    audit_run_id=run.id,
                    finding_id=None,
                    title='Close gap',
                    description='Patch the issue',
                    status='open',
                    sla_due_at=datetime.now(UTC) - timedelta(days=1),
                )
            )
            await append_audit_log(
                db,
                org_id=seeded_ids['org_id'],
                actor_user_id=None,
                action='audit_run.complete',
                entity_type='audit_run',
                entity_id=run.id,
                payload={'status': 'completed'},
            )
            await db.commit()

    asyncio.run(_seed())

    token = _login(client, seeded_ids['users']['admin'], seeded_ids['org_id'])
    response = client.get(
        f"/organizations/{seeded_ids['org_id']}/dashboard",
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['org_id'] == seeded_ids['org_id']
    assert payload['summary']['projects_total'] == 1
    assert payload['summary']['completed_runs'] == 1
    assert payload['summary']['critical_findings'] == 1
    assert payload['summary']['quarantined_evidence'] == 1
    assert payload['summary']['audit_coverage_pct'] == 100
    assert payload['plan']['plan_code'] == 'growth'
    assert payload['plan']['asset_usage_pct'] == 25
    assert payload['recent_runs'][0]['project_id'] == seeded_ids['project_id']
    assert payload['recent_activity'][0]['action'] == 'audit_run.complete'
    assert payload['legal']['dpa_status'] == 'pending'
    assert any(
        item['key'] == 'dpa_gate' and item['ready'] is False for item in payload['readiness']['items']
    )
    assert payload['readiness']['score'] == 33


def test_dashboard_assistant_route_is_not_exposed(client, seeded_ids):
    token = _login(client, seeded_ids['users']['admin'], seeded_ids['org_id'])
    response = client.post(
        f"/organizations/{seeded_ids['org_id']}/assistant/chat",
        headers={'Authorization': f'Bearer {token}'},
        json={'messages': [{'role': 'user', 'content': 'Que deberia arreglar primero?'}]},
    )

    assert response.status_code == 404, response.text
