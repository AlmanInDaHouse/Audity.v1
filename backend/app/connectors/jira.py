from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit_log import append_audit_log
from app.models import ExternalTicket, Finding, FindingStatusEnum, OutboundIntegration, Project, RemediationTask
from app.secret_store import SecretStoreError, get_secret_store


@dataclass
class JiraIssue:
    key: str
    browse_url: str
    raw: dict[str, Any]


@dataclass
class JiraConnectorConfig:
    base_url: str
    project_key: str
    issue_type: str
    closed_statuses: set[str]
    webhook_secret: str | None
    labels: list[str]

    @classmethod
    def from_integration(cls, integration: OutboundIntegration) -> 'JiraConnectorConfig':
        config = integration.config_json or {}
        return cls(
            base_url=str(config.get('base_url', '')).rstrip('/'),
            project_key=str(config.get('project_key', 'AUD')).strip(),
            issue_type=str(config.get('issue_type', 'Task')).strip(),
            closed_statuses={str(item).lower() for item in config.get('closed_statuses', ['done', 'closed', 'resolved'])},
            webhook_secret=str(config.get('webhook_secret', '')).strip() or None,
            labels=[str(item) for item in config.get('labels', ['audity', 'grc'])][:10],
        )


class JiraClient:
    def __init__(self, *, base_url: str, auth_token: str) -> None:
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token

    @property
    def headers(self) -> dict[str, str]:
        return {
            'Authorization': f'Bearer {self.auth_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

    async def create_issue(
        self,
        *,
        project_key: str,
        issue_type: str,
        summary: str,
        description: str,
        labels: list[str],
    ) -> JiraIssue:
        payload = {
            'fields': {
                'project': {'key': project_key},
                'summary': summary,
                'issuetype': {'name': issue_type},
                'description': {
                    'type': 'doc',
                    'version': 1,
                    'content': [
                        {
                            'type': 'paragraph',
                            'content': [{'type': 'text', 'text': description[:32000]}],
                        }
                    ],
                },
                'labels': labels,
            }
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f'{self.base_url}/rest/api/3/issue', headers=self.headers, json=payload)
            response.raise_for_status()
        body = response.json()
        key = str(body['key'])
        return JiraIssue(key=key, browse_url=f'{self.base_url}/browse/{key}', raw=body)


async def _resolve_token(integration: OutboundIntegration) -> str:
    config = integration.config_json or {}
    if integration.secret_ref:
        try:
            return await get_secret_store().get(integration.secret_ref)
        except SecretStoreError as exc:
            raise RuntimeError(f'Unable to read Jira secret_ref: {exc}') from exc
    token = str(config.get('api_token', '')).strip()
    if not token:
        raise RuntimeError('Jira connector requires secret_ref or config_json.api_token')
    return token


async def sync_finding_to_jira(
    db: AsyncSession,
    *,
    integration: OutboundIntegration,
    project: Project,
    finding: Finding,
    task: RemediationTask | None,
) -> ExternalTicket | None:
    existing = await db.scalar(
        select(ExternalTicket).where(
            ExternalTicket.finding_id == finding.id,
            ExternalTicket.outbound_integration_id == integration.id,
        )
    )
    if existing is not None or not integration.is_enabled:
        return existing

    config = JiraConnectorConfig.from_integration(integration)
    if not config.base_url:
        raise RuntimeError('Jira connector missing config_json.base_url')

    token = await _resolve_token(integration)
    client = JiraClient(base_url=config.base_url, auth_token=token)
    summary = f'[Audity] {finding.control_id} - {finding.title}'
    description = (
        f'Project: {project.name}\n'
        f'Control: {finding.control_id}\n'
        f'Severity: {finding.severity.value}\n'
        f'Result: {finding.result.value}\n'
        f'Finding ID: {finding.id}\n'
        f'Remediation: {(task.description if task else finding.notes) or "Pending triage"}'
    )
    issue = await client.create_issue(
        project_key=config.project_key,
        issue_type=config.issue_type,
        summary=summary,
        description=description,
        labels=config.labels + [finding.severity.value, finding.control_id.lower().replace('.', '-')],
    )
    external = ExternalTicket(
        org_id=finding.org_id,
        finding_id=finding.id,
        outbound_integration_id=integration.id,
        provider='jira',
        external_key=issue.key,
        external_url=issue.browse_url,
        external_status='open',
        sync_state='linked',
        last_payload_json=issue.raw,
    )
    db.add(external)
    await db.flush()
    await append_audit_log(
        db,
        org_id=finding.org_id,
        actor_user_id=None,
        action='connector.jira.issue_created',
        entity_type='finding',
        entity_id=finding.id,
        payload={'issue_key': issue.key, 'integration_id': integration.id},
    )
    return external


async def handle_jira_webhook(
    db: AsyncSession,
    *,
    integration: OutboundIntegration,
    payload: dict[str, Any],
    provided_secret: str | None,
) -> dict[str, Any]:
    config = JiraConnectorConfig.from_integration(integration)
    if config.webhook_secret and not secrets.compare_digest(config.webhook_secret, provided_secret or ''):
        raise PermissionError('Invalid Jira webhook secret')

    issue = payload.get('issue') or {}
    fields = issue.get('fields') or {}
    status_name = str((fields.get('status') or {}).get('name', '')).strip()
    issue_key = str(issue.get('key', '')).strip()
    if not issue_key:
        raise ValueError('Webhook payload missing issue.key')

    ticket = await db.scalar(
        select(ExternalTicket).where(
            ExternalTicket.outbound_integration_id == integration.id,
            ExternalTicket.external_key == issue_key,
        )
    )
    if ticket is None:
        return {'matched': False, 'issue_key': issue_key}

    ticket.external_status = status_name or ticket.external_status
    ticket.last_payload_json = payload
    ticket.sync_state = 'closed_upstream' if status_name.lower() in config.closed_statuses else 'linked'

    finding = await db.get(Finding, ticket.finding_id)
    if finding is not None and status_name.lower() in config.closed_statuses:
        finding.status = FindingStatusEnum.pending_validation
        tasks = (
            await db.execute(select(RemediationTask).where(RemediationTask.finding_id == finding.id, RemediationTask.org_id == finding.org_id))
        ).scalars().all()
        for task in tasks:
            task.status = 'pending_validation'
        await append_audit_log(
            db,
            org_id=finding.org_id,
            actor_user_id=None,
            action='connector.jira.closed_upstream',
            entity_type='finding',
            entity_id=finding.id,
            payload={'issue_key': issue_key, 'status': status_name},
        )

    await db.flush()
    return {'matched': True, 'issue_key': issue_key, 'status': status_name}
