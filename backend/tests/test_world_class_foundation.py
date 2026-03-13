from __future__ import annotations

import asyncio

import pytest

from app.catalog_engine import compute_catalog_checksum, load_controls
from app import main as main_module
from app.connectors import jira as jira_module
from app.db import SessionLocal
from app.knowledge_engine import evaluate_manual_evidence
from app.models import ExternalTicket, Finding, FindingStatusEnum, RemediationTask
from app.package_export import HTML, build_executive_report
from app.storage import get_object_store
from app.temporal_workflow import AuditRunWorkflowInput
from app.workflow_runtime import AuditWorkflowInput, execute_inline


def test_ai_evaluator_uses_structured_heuristic_fallback():
    async def _run() -> dict:
        store = get_object_store()
        await store.put_bytes('evidence/test/policy.txt', b'Information security policy approved by management.', 'text/plain')
        return await evaluate_manual_evidence(
            [
                {
                    'id': 'ev-1',
                    'name': 'security-policy.txt',
                    'object_key': 'evidence/test/policy.txt',
                    'content_type': 'text/plain',
                    'metadata': {'content_type': 'text/plain'},
                }
            ]
        )

    payload = asyncio.run(_run())
    assert payload['assessments']
    first = payload['assessments'][0]
    assert first['control_id'].startswith('ISO-')
    assert first['verdict'] in {'cumple', 'recomendacion'}


def test_executive_report_builder_returns_pdf_bytes():
    if HTML is None:
        pytest.skip('WeasyPrint runtime unavailable in local interpreter')
    artifact = build_executive_report(
        org_id='org-1',
        project_name='Main Project',
        audit_run_id='run-1',
        risk_score=42.0,
        risk_level='medium',
        findings=[{'control_id': 'ISO-A.5.1', 'title': 'Policy', 'severity': 'high', 'result': 'fail', 'notes': 'Missing'}],
        remediation_tasks=[{'title': 'Write policy', 'description': 'Approve and publish policy', 'status': 'open'}],
        evidence_summary={'manual': [{'id': 'ev-1'}]},
    )
    assert '<html' in artifact.html.lower()
    assert artifact.pdf.startswith(b'%PDF')
    assert len(artifact.pdf) > 1024


def test_iso_catalog_has_market_ready_depth():
    controls = [item for item in load_controls() if item.framework == 'ISO27001']

    assert len(controls) >= 30
    assert all(control.title and control.description for control in controls)
    assert all(control.tags for control in controls)
    assert all(control.evidence_requirements for control in controls)
    assert all(control.evaluator_key for control in controls)
    assert len(compute_catalog_checksum()) == 64


def test_jira_ticket_creation_and_webhook_feedback(client, seeded_ids, monkeypatch):
    if HTML is None:
        pytest.skip('WeasyPrint runtime unavailable in local interpreter')

    async def _launch_inline(payload: AuditRunWorkflowInput) -> None:
        await execute_inline(AuditWorkflowInput(**payload.__dict__))

    async def _fake_create_issue(self, *, project_key: str, issue_type: str, summary: str, description: str, labels: list[str]):
        return jira_module.JiraIssue(
            key='AUD-101',
            browse_url='https://jira.example.local/browse/AUD-101',
            raw={'project_key': project_key, 'issue_type': issue_type, 'summary': summary, 'labels': labels},
        )

    monkeypatch.setattr(main_module, 'launch_audit_workflow', _launch_inline)
    monkeypatch.setattr(jira_module.JiraClient, 'create_issue', _fake_create_issue)

    admin_token = client.post(
        '/auth/mock/login',
        json={'email': seeded_ids['users']['admin'], 'org_id': seeded_ids['org_id']},
    ).json()['access_token']
    admin_headers = {'Authorization': f'Bearer {admin_token}'}

    create_integration = client.post(
        f"/organizations/{seeded_ids['org_id']}/outbound-integrations",
        json={
            'kind': 'jira',
            'name': 'Corporate Jira',
            'config_json': {
                'base_url': 'https://jira.example.local',
                'project_key': 'AUD',
                'issue_type': 'Task',
                'webhook_secret': 'shared-secret',
                'api_token': 'mock-token',
            },
            'is_enabled': True,
            'secret_ref': None,
        },
        headers=admin_headers,
    )
    assert create_integration.status_code == 200, create_integration.text
    integration_id = create_integration.json()['id']

    auditor_token = client.post(
        '/auth/mock/login',
        json={'email': seeded_ids['users']['auditor'], 'org_id': seeded_ids['org_id'], 'mfa': True},
    ).json()['access_token']
    auditor_headers = {'Authorization': f'Bearer {auditor_token}'}
    run = client.post(
        f"/projects/{seeded_ids['project_id']}/audit-runs",
        json={'catalog_version': 'v1'},
        headers=auditor_headers,
    )
    assert run.status_code == 200, run.text

    async def _assert_ticket_created() -> tuple[str, str]:
        async with SessionLocal() as db:
            from app.models import AuditLogEntry
            from sqlalchemy import select
            logs = (await db.execute(select(AuditLogEntry).order_by(AuditLogEntry.created_at.desc()).limit(10))).scalars().all()
            for l in logs: print(f"LOGGED: {l.action} -> {l.payload_json}")

            finding = (await db.execute(Finding.__table__.select())).mappings().first()
            ticket = (await db.execute(ExternalTicket.__table__.select())).mappings().first()
            assert finding is not None
            assert ticket is not None
            assert ticket['external_key'] == 'AUD-101'
            return finding['id'], ticket['outbound_integration_id']

    finding_id, outbound_integration_id = asyncio.run(_assert_ticket_created())
    assert outbound_integration_id == integration_id

    webhook = client.post(
        f'/webhooks/jira/{integration_id}?secret=shared-secret',
        json={'issue': {'key': 'AUD-101', 'fields': {'status': {'name': 'Closed'}}}},
    )
    assert webhook.status_code == 200, webhook.text
    assert webhook.json()['matched'] is True

    async def _assert_feedback_applied() -> None:
        async with SessionLocal() as db:
            finding = await db.get(Finding, finding_id)
            task = (await db.execute(RemediationTask.__table__.select())).mappings().first()
            assert finding is not None
            assert finding.status == FindingStatusEnum.pending_validation
            assert task is not None
            assert task['status'] == 'pending_validation'

    asyncio.run(_assert_feedback_applied())
