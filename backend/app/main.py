from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit_log import append_audit_log
from app.auth_sessions import issue_session
from app.av_scanner import scan_upload_activity
from app.config import get_settings, validate_runtime_security
from app.db import Base, engine, get_db
from app.deps import UserContext, get_current_user, require_mfa, require_roles
from app.enterprise import router as enterprise_router
from app.models import (
    AuditLogEntry,
    AuditRun,
    AuditStatusEnum,
    ControlCatalog,
    EvidenceItem,
    Finding,
    Integration,
    Membership,
    Organization,
    OrgSecurityPolicy,
    OutboundIntegration,
    PricingPlan,
    Project,
    RemediationTask,
    RoleEnum,
    SeverityEnum,
    User,
)
from app.otel import setup_otel
from app.permissions import require_permission
from app.rate_limit import enforce_sensitive_limit, rate_limit_middleware, rate_limiter
from app.schemas import (
    AuditRunCreate,
    ControlCatalogCreate,
    IntegrationCreate,
    IntegrationUpdate,
    LoginRequest,
    OrganizationCreate,
    ProjectCreate,
    ProjectUpdate,
)
from app.security import get_signer
from app.signing import sign_manifest
from app.storage import get_object_store
from app.telemetry import UPLOAD_QUARANTINED, render_metrics, telemetry_middleware
from app.temporal_workflow import AuditRunWorkflowInput
from app.tenancy import set_current_org
from app.workflow_launcher import launch_audit_workflow

settings = get_settings()
ALLOWED_UPLOAD_MIME_TYPES = {
    'application/pdf',
    'text/plain',
    'text/csv',
    'application/json',
    'image/png',
    'image/jpeg',
}

app = FastAPI(title='Audity API', version='0.1.0')
_cors_origins = [o.strip() for o in settings.cors_allowed_origins.split(',') if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.middleware('http')(rate_limit_middleware)
if settings.metrics_enabled:
    app.middleware('http')(telemetry_middleware)


@app.middleware('http')
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response


@app.on_event('startup')
async def startup() -> None:
    validate_runtime_security(settings)
    setup_otel(app)
    await rate_limiter.startup()
    store = get_object_store()
    await store.ensure_bucket()
    if settings.auto_create_schema:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


@app.on_event('shutdown')
async def shutdown() -> None:
    await rate_limiter.shutdown()


app.include_router(enterprise_router)


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/metrics')
async def metrics() -> Response:
    return render_metrics()


@app.get('/.well-known/openid-configuration')
async def oidc_configuration(request: Request) -> dict[str, Any]:
    base = settings.oidc_issuer.rstrip('/')
    payload: dict[str, Any] = {
        'issuer': base,
        'jwks_uri': f'{base}/jwks.json',
        'id_token_signing_alg_values_supported': ['RS256'],
    }
    if settings.oidc_token_endpoint:
        payload['token_endpoint'] = settings.oidc_token_endpoint
    elif settings.is_mock_login_enabled:
        payload['token_endpoint'] = f'{base}/auth/mock/login'
    return payload


@app.get('/jwks.json')
async def jwks() -> dict[str, Any]:
    return get_signer().jwks()


@app.get('/auth/config')
async def auth_config() -> dict[str, Any]:
    return {
        'mock_login_enabled': settings.is_mock_login_enabled,
        'enterprise_auth_enabled': settings.feature_auth_enterprise,
        'demo_org_id': settings.demo_org_id,
    }


@app.post('/auth/mock/login')
async def mock_login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    if not settings.is_mock_login_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Mock login is disabled in this environment')
    await set_current_org(db, payload.org_id)
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unknown user')

    membership = await db.scalar(
        select(Membership).where(Membership.user_id == user.id, Membership.org_id == payload.org_id)
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User not member of organization')

    refresh_token, session = await issue_session(db, user=user, org_id=payload.org_id)
    token = get_signer().token(
        sub=user.id,
        email=user.email,
        org_id=payload.org_id,
        role=membership.role.value,
        sid=session.id,
        mfa=payload.mfa,
    )
    await db.commit()
    return {
        'access_token': token,
        'refresh_token': refresh_token,
        'session_id': session.id,
        'token_type': 'bearer',
        'expires_in': settings.access_token_ttl_minutes * 60,
    }


def _org_to_dict(org: Organization) -> dict[str, Any]:
    return {'id': org.id, 'name': org.name}


def _project_to_dict(item: Project) -> dict[str, Any]:
    return {
        'id': item.id,
        'org_id': item.org_id,
        'name': item.name,
        'description': item.description,
        'criticality': item.criticality.value,
        'created_at': item.created_at.isoformat(),
    }


def _integration_to_dict(item: Integration) -> dict[str, Any]:
    return {
        'id': item.id,
        'org_id': item.org_id,
        'project_id': item.project_id,
        'provider': item.provider,
        'name': item.name,
        'config_json': item.config_json,
        'secret_ref': item.secret_ref,
        'is_enabled': item.is_enabled,
        'created_at': item.created_at.isoformat(),
    }


def _contains_plaintext_secret(config_json: dict[str, Any]) -> bool:
    for key, value in config_json.items():
        normalized = key.lower()
        if any(marker in normalized for marker in ('secret', 'token', 'password', 'private_key')):
            if isinstance(value, str) and value.strip():
                return True
    return False


def _catalog_to_dict(item: ControlCatalog) -> dict[str, Any]:
    return {
        'id': item.id,
        'org_id': item.org_id,
        'name': item.name,
        'framework': item.framework,
        'version': item.version,
        'checksum': item.checksum,
        'source_path': item.source_path,
        'is_global': item.is_global,
    }


def _audit_run_to_dict(item: AuditRun) -> dict[str, Any]:
    return {
        'id': item.id,
        'org_id': item.org_id,
        'project_id': item.project_id,
        'status': item.status.value,
        'catalog_version': item.catalog_version,
        'progress_json': item.progress_json,
        'summary_json': item.summary_json,
        'risk_score': item.risk_score,
        'risk_level': item.risk_level,
        'report_evidence_id': item.report_evidence_id,
        'signature_bundle_json': item.signature_bundle_json,
        'created_at': item.created_at.isoformat(),
        'updated_at': item.updated_at.isoformat(),
    }


def _percentage(part: int, total: int) -> int:
    if total <= 0:
        return 0
    return round((part / total) * 100)


async def _load_portfolio_snapshot(org_id: str, db: AsyncSession) -> dict[str, Any]:
    projects = (
        await db.execute(
            select(Project).where(Project.org_id == org_id).order_by(Project.created_at.desc())
        )
    ).scalars().all()
    project_ids = [project.id for project in projects]
    runs = (
        await db.execute(
            select(AuditRun)
            .where(AuditRun.org_id == org_id, AuditRun.project_id.in_(project_ids) if project_ids else False)
            .order_by(AuditRun.updated_at.desc())
        )
    ).scalars().all()

    latest_by_project: dict[str, AuditRun] = {}
    runs_by_project: dict[str, list[AuditRun]] = {}
    for run in runs:
        latest_by_project.setdefault(run.project_id, run)
        runs_by_project.setdefault(run.project_id, []).append(run)

    project_rows = []
    run_rows = []
    report_rows = []
    project_name_by_id = {project.id: project.name for project in projects}

    for project in projects:
        latest_run = latest_by_project.get(project.id)
        project_runs = runs_by_project.get(project.id, [])
        project_rows.append(
            {
                'project': _project_to_dict(project),
                'latest_run': _audit_run_to_dict(latest_run) if latest_run else None,
                'runs_total': len(project_runs),
                'completed_runs': len([run for run in project_runs if run.status == AuditStatusEnum.completed]),
            }
        )

    for run in runs:
        row = {
            'project': {
                'id': run.project_id,
                'name': project_name_by_id.get(run.project_id, 'Unknown project'),
            },
            'run': _audit_run_to_dict(run),
        }
        run_rows.append(row)
        if run.status == AuditStatusEnum.completed and run.report_evidence_id:
            report_rows.append(row)

    return {
        'projects': project_rows,
        'audit_runs': run_rows,
        'reports': report_rows,
    }


@app.get('/organizations')
async def list_organizations(
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    memberships = (
        await db.execute(select(Membership).where(Membership.user_id == ctx.user_id))
    ).scalars().all()
    org_ids = [m.org_id for m in memberships]
    if not org_ids:
        return []
    orgs = (await db.execute(select(Organization).where(Organization.id.in_(org_ids)))).scalars().all()
    return [_org_to_dict(org) for org in orgs]


async def _load_organization_dashboard(org_id: str, db: AsyncSession) -> dict[str, Any]:
    organization = await db.get(Organization, org_id)
    if organization is None:
        raise HTTPException(status_code=404, detail='Organization not found')

    plan = await db.get(PricingPlan, org_id)
    policy = await db.get(OrgSecurityPolicy, org_id)

    total_projects = int(
        await db.scalar(select(func.count()).select_from(Project).where(Project.org_id == org_id)) or 0
    )
    total_runs = int(
        await db.scalar(select(func.count()).select_from(AuditRun).where(AuditRun.org_id == org_id)) or 0
    )
    active_runs = int(
        await db.scalar(
            select(func.count())
            .select_from(AuditRun)
            .where(
                AuditRun.org_id == org_id,
                AuditRun.status.in_([AuditStatusEnum.queued, AuditStatusEnum.running]),
            )
        )
        or 0
    )
    completed_runs = int(
        await db.scalar(
            select(func.count())
            .select_from(AuditRun)
            .where(AuditRun.org_id == org_id, AuditRun.status == AuditStatusEnum.completed)
        )
        or 0
    )
    total_evidence = int(
        await db.scalar(select(func.count()).select_from(EvidenceItem).where(EvidenceItem.org_id == org_id)) or 0
    )
    clean_evidence = int(
        await db.scalar(
            select(func.count())
            .select_from(EvidenceItem)
            .where(EvidenceItem.org_id == org_id, EvidenceItem.scan_status == 'clean')
        )
        or 0
    )
    quarantined_evidence = max(total_evidence - clean_evidence, 0)
    project_integrations = int(
        await db.scalar(select(func.count()).select_from(Integration).where(Integration.org_id == org_id)) or 0
    )
    outbound_integrations = int(
        await db.scalar(select(func.count()).select_from(OutboundIntegration).where(OutboundIntegration.org_id == org_id))
        or 0
    )
    projects_with_integrations = int(
        await db.scalar(
            select(func.count(func.distinct(Integration.project_id))).where(
                Integration.org_id == org_id,
                Integration.is_enabled.is_(True),
            )
        )
        or 0
    )
    projects_with_completed_runs = int(
        await db.scalar(
            select(func.count(func.distinct(AuditRun.project_id))).where(
                AuditRun.org_id == org_id,
                AuditRun.status == AuditStatusEnum.completed,
            )
        )
        or 0
    )
    open_findings = int(
        await db.scalar(
            select(func.count()).select_from(Finding).where(Finding.org_id == org_id, Finding.status == 'open')
        )
        or 0
    )
    critical_findings = int(
        await db.scalar(
            select(func.count())
            .select_from(Finding)
            .where(
                Finding.org_id == org_id,
                Finding.status == 'open',
                Finding.severity == SeverityEnum.high,
            )
        )
        or 0
    )
    overdue_tasks = int(
        await db.scalar(
            select(func.count())
            .select_from(RemediationTask)
            .where(
                RemediationTask.org_id == org_id,
                RemediationTask.status != 'resolved',
                RemediationTask.sla_due_at.is_not(None),
                RemediationTask.sla_due_at < datetime.now(UTC),
            )
        )
        or 0
    )

    recent_runs = (
        await db.execute(
            select(AuditRun, Project.name)
            .join(Project, Project.id == AuditRun.project_id)
            .where(AuditRun.org_id == org_id)
            .order_by(AuditRun.updated_at.desc())
            .limit(6)
        )
    ).all()
    recent_activity = (
        await db.execute(
            select(AuditLogEntry)
            .where(AuditLogEntry.org_id == org_id)
            .order_by(AuditLogEntry.created_at.desc())
            .limit(8)
        )
    ).scalars().all()

    max_assets = plan.max_assets if plan is not None else 50
    module_flags = plan.modules_json if plan is not None else {}
    enabled_modules = sorted([key for key, enabled in module_flags.items() if enabled])

    readiness_items = [
        {
            'key': 'workflow_coverage',
            'label': 'Workflow coverage',
            'ready': projects_with_completed_runs > 0,
            'detail': f'{projects_with_completed_runs}/{total_projects} projects have completed audits',
        },
        {
            'key': 'integration_coverage',
            'label': 'Integration coverage',
            'ready': projects_with_integrations > 0,
            'detail': f'{projects_with_integrations}/{total_projects} projects have enabled integrations',
        },
        {
            'key': 'security_policy',
            'label': 'Security policy',
            'ready': bool(policy and policy.require_mfa_sensitive),
            'detail': 'Sensitive actions protected with MFA policy',
        },
        {
            'key': 'evidence_integrity',
            'label': 'Evidence integrity',
            'ready': settings.feature_signing and clean_evidence > 0,
            'detail': f'{clean_evidence}/{total_evidence} evidence items passed integrity-safe download flow',
        },
        {
            'key': 'dpa_gate',
            'label': 'DPA gate',
            'ready': organization.dpa_status == 'signed',
            'detail': 'Customer onboarding remains blocked until a signed DPA is registered',
        },
        {
            'key': 'enterprise_controls',
            'label': 'Enterprise controls',
            'ready': settings.enterprise_features_enabled,
            'detail': 'Enterprise controls feature gate available',
        },
    ]
    readiness_score = _percentage(sum(1 for item in readiness_items if item['ready']), len(readiness_items))

    return {
        'org_id': organization.id,
        'org_name': organization.name,
        'generated_at': datetime.now(UTC).isoformat(),
        'legal': {
            'dpa_status': organization.dpa_status,
            'dpa_reference': organization.dpa_reference,
            'dpa_signed_at': organization.dpa_signed_at.isoformat() if organization.dpa_signed_at else None,
            'onboarding_status': organization.onboarding_status,
            'onboarding_completed_at': organization.onboarding_completed_at.isoformat() if organization.onboarding_completed_at else None,
        },
        'summary': {
            'projects_total': total_projects,
            'audit_runs_total': total_runs,
            'active_runs': active_runs,
            'completed_runs': completed_runs,
            'evidence_total': total_evidence,
            'quarantined_evidence': quarantined_evidence,
            'open_findings': open_findings,
            'critical_findings': critical_findings,
            'overdue_tasks': overdue_tasks,
            'project_integrations': project_integrations,
            'outbound_integrations': outbound_integrations,
            'audit_coverage_pct': _percentage(projects_with_completed_runs, total_projects),
            'automation_coverage_pct': _percentage(projects_with_integrations, total_projects),
            'evidence_hygiene_pct': _percentage(clean_evidence, total_evidence),
        },
        'plan': {
            'plan_code': plan.plan_code if plan is not None else 'starter',
            'max_assets': max_assets,
            'assets_used': total_projects,
            'asset_usage_pct': _percentage(total_projects, max_assets),
            'max_upload_bytes': plan.max_upload_bytes if plan is not None else 20 * 1024 * 1024,
            'modules_enabled': enabled_modules,
        },
        'readiness': {
            'score': readiness_score,
            'items': readiness_items,
        },
        'recent_runs': [
            {
                'id': run.id,
                'project_id': run.project_id,
                'project_name': project_name,
                'status': run.status.value,
                'risk_score': run.risk_score,
                'risk_level': run.risk_level,
                'updated_at': run.updated_at.isoformat(),
            }
            for run, project_name in recent_runs
        ],
        'recent_activity': [
            {
                'id': row.id,
                'action': row.action,
                'entity_type': row.entity_type,
                'entity_id': row.entity_id,
                'created_at': row.created_at.isoformat(),
            }
            for row in recent_activity
        ],
    }


@app.get('/organizations/{org_id}/dashboard')
async def get_organization_dashboard(
    org_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if org_id != ctx.org_id:
        raise HTTPException(status_code=403, detail='Cross-tenant access denied')
    return await _load_organization_dashboard(org_id, db)


@app.post('/organizations')
async def create_organization(
    payload: OrganizationCreate,
    ctx: UserContext = Depends(require_roles('org_admin')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    org = Organization(name=payload.name, dpa_status='pending', onboarding_status='pending_dpa')
    db.add(org)
    await db.flush()

    membership = Membership(org_id=org.id, user_id=ctx.user_id, role=RoleEnum.org_admin)
    db.add(membership)
    db.add(OrgSecurityPolicy(org_id=org.id))
    db.add(PricingPlan(org_id=org.id))

    await append_audit_log(
        db,
        org_id=org.id,
        actor_user_id=ctx.user_id,
        action='organization.create',
        entity_type='organization',
        entity_id=org.id,
        payload={'name': org.name},
    )
    await db.commit()
    return _org_to_dict(org)


async def _project_for_org(db: AsyncSession, project_id: str, org_id: str) -> Project:
    project = await db.scalar(select(Project).where(Project.id == project_id, Project.org_id == org_id))
    if project is None:
        raise HTTPException(status_code=404, detail='Project not found')
    return project


@app.get('/organizations/{org_id}/projects')
async def list_projects(
    org_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    if org_id != ctx.org_id:
        raise HTTPException(status_code=403, detail='Cross-tenant access denied')
    rows = (await db.execute(select(Project).where(Project.org_id == org_id))).scalars().all()
    return [_project_to_dict(row) for row in rows]


@app.get('/organizations/{org_id}/portfolio')
async def get_portfolio_snapshot(
    org_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if org_id != ctx.org_id:
        raise HTTPException(status_code=403, detail='Cross-tenant access denied')
    return await _load_portfolio_snapshot(org_id, db)


@app.post('/organizations/{org_id}/projects')
async def create_project(
    org_id: str,
    payload: ProjectCreate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if org_id != ctx.org_id:
        raise HTTPException(status_code=403, detail='Cross-tenant access denied')
    await require_permission(db, org_id=ctx.org_id, role=ctx.role, resource='project', action='write')

    project = Project(
        org_id=org_id,
        name=payload.name,
        description=payload.description,
        criticality=payload.criticality,
    )
    db.add(project)
    await db.flush()
    await append_audit_log(
        db,
        org_id=org_id,
        actor_user_id=ctx.user_id,
        action='project.create',
        entity_type='project',
        entity_id=project.id,
        payload={'name': payload.name},
    )
    await db.commit()
    return _project_to_dict(project)


@app.get('/projects/{project_id}')
async def get_project(
    project_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project = await _project_for_org(db, project_id, ctx.org_id)
    return _project_to_dict(project)


@app.patch('/projects/{project_id}')
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project = await _project_for_org(db, project_id, ctx.org_id)
    await require_permission(db, org_id=ctx.org_id, role=ctx.role, resource='project', action='write', project=project)
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    if payload.criticality is not None:
        project.criticality = payload.criticality

    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='project.update',
        entity_type='project',
        entity_id=project.id,
        payload=payload.model_dump(exclude_none=True),
    )
    await db.commit()
    return _project_to_dict(project)


@app.delete('/projects/{project_id}', status_code=204)
async def delete_project(
    project_id: str,
    ctx: UserContext = Depends(require_roles('org_admin')),
    db: AsyncSession = Depends(get_db),
) -> Response:
    project = await _project_for_org(db, project_id, ctx.org_id)
    await require_permission(db, org_id=ctx.org_id, role=ctx.role, resource='project', action='delete', project=project)
    await db.delete(project)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='project.delete',
        entity_type='project',
        entity_id=project.id,
    )
    await db.commit()
    return Response(status_code=204)


@app.get('/projects/{project_id}/integrations')
async def list_integrations(
    project_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _project_for_org(db, project_id, ctx.org_id)
    rows = (
        await db.execute(
            select(Integration).where(Integration.project_id == project_id, Integration.org_id == ctx.org_id)
        )
    ).scalars().all()
    return [_integration_to_dict(row) for row in rows]


@app.post('/projects/{project_id}/integrations')
async def create_integration(
    project_id: str,
    payload: IntegrationCreate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project = await _project_for_org(db, project_id, ctx.org_id)
    await require_permission(db, org_id=ctx.org_id, role=ctx.role, resource='project', action='write', project=project)
    integration = Integration(
        org_id=ctx.org_id,
        project_id=project_id,
        provider=payload.provider,
        name=payload.name,
        config_json=payload.config_json,
        secret_ref=payload.secret_ref,
        is_enabled=payload.is_enabled,
    )
    if _contains_plaintext_secret(payload.config_json):
        raise HTTPException(status_code=400, detail='config_json cannot contain plaintext secrets; use secret_ref')
    db.add(integration)
    await db.flush()
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='integration.create',
        entity_type='integration',
        entity_id=integration.id,
        payload={'provider': integration.provider},
    )
    await db.commit()
    return _integration_to_dict(integration)


@app.patch('/integrations/{integration_id}')
async def update_integration(
    integration_id: str,
    payload: IntegrationUpdate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    integration = await db.scalar(
        select(Integration).where(Integration.id == integration_id, Integration.org_id == ctx.org_id)
    )
    if integration is None:
        raise HTTPException(status_code=404, detail='Integration not found')
    await require_permission(db, org_id=ctx.org_id, role=ctx.role, resource='project', action='write')

    for field, value in payload.model_dump(exclude_none=True).items():
        if field == 'config_json' and isinstance(value, dict) and _contains_plaintext_secret(value):
            raise HTTPException(status_code=400, detail='config_json cannot contain plaintext secrets; use secret_ref')
        setattr(integration, field, value)

    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='integration.update',
        entity_type='integration',
        entity_id=integration.id,
        payload=payload.model_dump(exclude_none=True),
    )
    await db.commit()
    return _integration_to_dict(integration)


@app.delete('/integrations/{integration_id}', status_code=204)
async def delete_integration(
    integration_id: str,
    ctx: UserContext = Depends(require_roles('org_admin')),
    db: AsyncSession = Depends(get_db),
) -> Response:
    integration = await db.scalar(
        select(Integration).where(Integration.id == integration_id, Integration.org_id == ctx.org_id)
    )
    if integration is None:
        raise HTTPException(status_code=404, detail='Integration not found')
    await require_permission(db, org_id=ctx.org_id, role=ctx.role, resource='project', action='delete')
    await db.delete(integration)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='integration.delete',
        entity_type='integration',
        entity_id=integration.id,
    )
    await db.commit()
    return Response(status_code=204)


@app.get('/control-catalogs')
async def list_control_catalogs(
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(ControlCatalog).where((ControlCatalog.org_id == ctx.org_id) | (ControlCatalog.is_global.is_(True)))
        )
    ).scalars().all()
    return [_catalog_to_dict(row) for row in rows]


@app.post('/control-catalogs')
async def create_control_catalog(
    payload: ControlCatalogCreate,
    ctx: UserContext = Depends(require_roles('org_admin', 'auditor')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    catalog = ControlCatalog(
        org_id=None if payload.is_global else ctx.org_id,
        name=payload.name,
        framework=payload.framework,
        version=payload.version,
        checksum=payload.checksum,
        source_path=payload.source_path,
        is_global=payload.is_global,
    )
    db.add(catalog)
    await db.flush()
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='catalog.create',
        entity_type='control_catalog',
        entity_id=catalog.id,
        payload={'framework': payload.framework, 'version': payload.version},
    )
    await db.commit()
    return _catalog_to_dict(catalog)


@app.delete('/control-catalogs/{catalog_id}', status_code=204)
async def delete_control_catalog(
    catalog_id: str,
    ctx: UserContext = Depends(require_roles('org_admin')),
    db: AsyncSession = Depends(get_db),
) -> Response:
    catalog = await db.scalar(
        select(ControlCatalog).where(
            ControlCatalog.id == catalog_id,
            (ControlCatalog.org_id == ctx.org_id) | (ControlCatalog.is_global.is_(True)),
        )
    )
    if catalog is None:
        raise HTTPException(status_code=404, detail='Catalog not found')
    if catalog.is_global and catalog.org_id != ctx.org_id:
        raise HTTPException(status_code=403, detail='Cannot delete global catalogs')
    await db.delete(catalog)
    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='catalog.delete',
        entity_type='control_catalog',
        entity_id=catalog.id,
    )
    await db.commit()
    return Response(status_code=204)


@app.post('/projects/{project_id}/audit-runs')
async def create_audit_run(
    project_id: str,
    payload: AuditRunCreate,
    request: Request,
    ctx: UserContext = Depends(require_mfa),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await enforce_sensitive_limit(request, org_id=ctx.org_id, user_id=ctx.user_id)
    project = await _project_for_org(db, project_id, ctx.org_id)
    await require_permission(db, org_id=ctx.org_id, role=ctx.role, resource='audit_run', action='launch', project=project)

    run = AuditRun(
        org_id=ctx.org_id,
        project_id=project_id,
        triggered_by_user_id=ctx.user_id,
        status=AuditStatusEnum.queued,
        catalog_version=payload.catalog_version,
        progress_json={'stage': 'queued', 'queued_at': datetime.now(UTC).isoformat()},
        summary_json={},
    )
    db.add(run)
    await db.flush()

    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='audit_run.create',
        entity_type='audit_run',
        entity_id=run.id,
        payload={'project_id': project_id, 'catalog_version': payload.catalog_version},
    )
    await db.commit()

    wf_input = AuditRunWorkflowInput(
        org_id=ctx.org_id,
        project_id=project_id,
        audit_run_id=run.id,
        actor_user_id=ctx.user_id,
        catalog_version=payload.catalog_version,
    )
    await launch_audit_workflow(wf_input)
    return _audit_run_to_dict(run)


@app.get('/projects/{project_id}/audit-runs')
async def list_audit_runs(
    project_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _project_for_org(db, project_id, ctx.org_id)
    offset = (page - 1) * page_size

    total = await db.scalar(
        select(func.count())
        .select_from(AuditRun)
        .where(
            AuditRun.org_id == ctx.org_id,
            AuditRun.project_id == project_id,
        )
    )
    rows = (
        await db.execute(
            select(AuditRun)
            .where(
                AuditRun.org_id == ctx.org_id,
                AuditRun.project_id == project_id,
            )
            .order_by(AuditRun.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()

    return {
        'items': [_audit_run_to_dict(row) for row in rows],
        'page': page,
        'page_size': page_size,
        'total': int(total or 0),
    }


@app.get('/projects/{project_id}/audit-runs/{run_id}')
async def get_audit_run(
    project_id: str,
    run_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    run = await db.scalar(
        select(AuditRun).where(
            AuditRun.id == run_id,
            AuditRun.project_id == project_id,
            AuditRun.org_id == ctx.org_id,
        )
    )
    if run is None:
        raise HTTPException(status_code=404, detail='Audit run not found')
    return _audit_run_to_dict(run)


@app.get('/projects/{project_id}/audit-runs/{run_id}/findings')
async def list_findings(
    project_id: str,
    run_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(Finding).where(
                Finding.org_id == ctx.org_id,
                Finding.project_id == project_id,
                Finding.audit_run_id == run_id,
            )
        )
    ).scalars().all()
    return [
        {
            'id': row.id,
            'org_id': row.org_id,
            'project_id': row.project_id,
            'audit_run_id': row.audit_run_id,
            'control_id': row.control_id,
            'title': row.title,
            'severity': row.severity.value,
            'result': row.result.value,
            'confidence': row.confidence,
            'notes': row.notes,
            'status': row.status.value,
            'evidence_refs_json': row.evidence_refs_json,
        }
        for row in rows
    ]


@app.get('/projects/{project_id}/audit-runs/{run_id}/remediation-tasks')
async def list_remediation_tasks(
    project_id: str,
    run_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(RemediationTask).where(
                RemediationTask.org_id == ctx.org_id,
                RemediationTask.project_id == project_id,
                RemediationTask.audit_run_id == run_id,
            )
        )
    ).scalars().all()
    return [
        {
            'id': row.id,
            'org_id': row.org_id,
            'project_id': row.project_id,
            'audit_run_id': row.audit_run_id,
            'finding_id': row.finding_id,
            'title': row.title,
            'description': row.description,
            'assignee_user_id': row.assignee_user_id,
            'due_date': row.due_date.isoformat() if row.due_date else None,
            'sla_due_at': row.sla_due_at.isoformat() if row.sla_due_at else None,
            'status': row.status,
            'created_at': row.created_at.isoformat(),
        }
        for row in rows
    ]


@app.post('/projects/{project_id}/evidence/upload')
async def upload_evidence(
    project_id: str,
    request: Request,
    file: UploadFile = File(...),
    item_type: str = Form(default='manual_upload'),
    metadata_json: str = Form(default='{}'),
    audit_run_id: str | None = Form(default=None),
    ctx: UserContext = Depends(require_mfa),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await enforce_sensitive_limit(request, org_id=ctx.org_id, user_id=ctx.user_id)
    project = await _project_for_org(db, project_id, ctx.org_id)
    await require_permission(db, org_id=ctx.org_id, role=ctx.role, resource='evidence', action='upload', project=project)

    contents = await file.read()
    policy = await db.get(OrgSecurityPolicy, ctx.org_id)
    plan = await db.get(PricingPlan, ctx.org_id)
    max_size = settings.upload_default_max_mb * 1024 * 1024
    if policy is not None:
        max_size = min(max_size, policy.max_upload_bytes)
    if plan is not None:
        max_size = min(max_size, plan.max_upload_bytes)
    if len(contents) > max_size:
        raise HTTPException(status_code=413, detail=f'File too large (max {max_size} bytes)')

    content_type = (file.content_type or 'application/octet-stream').split(';', 1)[0].strip().lower()
    if content_type not in ALLOWED_UPLOAD_MIME_TYPES:
        raise HTTPException(status_code=415, detail='Unsupported media type')

    try:
        metadata = json.loads(metadata_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail='metadata_json must be valid JSON') from exc

    key = f'evidence/{ctx.org_id}/{project_id}/{uuid.uuid4()}-{file.filename}'
    store = get_object_store()
    stored = await store.put_bytes(key, contents, content_type)

    scan_status = await scan_upload_activity(contents)
    quarantined = scan_status in {'infected', 'scan_error'}
    quarantine_reason = None if not quarantined else f'av_scan_{scan_status}'
    if quarantined:
        UPLOAD_QUARANTINED.labels(ctx.org_id).inc()

    retention_days = policy.retention_days if policy else 365
    retention_until = datetime.now(UTC) + timedelta(days=retention_days)
    manifest_payload = {
        'org_id': ctx.org_id,
        'project_id': project_id,
        'audit_run_id': audit_run_id,
        'filename': file.filename,
        'sha256': stored.sha256,
        'content_type': content_type,
        'size': stored.size,
        'uploaded_at': datetime.now(UTC).isoformat(),
    }
    signature_bundle = await sign_manifest(ctx.org_id, manifest_payload)

    evidence = EvidenceItem(
        org_id=ctx.org_id,
        project_id=project_id,
        audit_run_id=audit_run_id,
        integration_id=None,
        item_type=item_type,
        name=file.filename or 'uploaded-file',
        object_key=stored.key,
        sha256=stored.sha256,
        metadata_json={**metadata, 'content_type': content_type, 'size': stored.size},
        scan_status=scan_status,
        quarantine_reason=quarantine_reason,
        retention_until=retention_until,
        manifest_json=manifest_payload,
        signature_bundle_json=signature_bundle,
        created_by_user_id=ctx.user_id,
    )
    db.add(evidence)
    await db.flush()

    await append_audit_log(
        db,
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        action='evidence.upload',
        entity_type='evidence',
        entity_id=evidence.id,
        payload={'project_id': project_id, 'item_type': item_type, 'filename': evidence.name},
    )
    await db.commit()

    return {
        'id': evidence.id,
        'org_id': evidence.org_id,
        'project_id': evidence.project_id,
        'audit_run_id': evidence.audit_run_id,
        'integration_id': evidence.integration_id,
        'item_type': evidence.item_type,
        'name': evidence.name,
        'object_key': evidence.object_key,
        'sha256': evidence.sha256,
        'scan_status': evidence.scan_status,
        'quarantine_reason': evidence.quarantine_reason,
        'metadata_json': evidence.metadata_json,
        'signature_bundle_json': evidence.signature_bundle_json,
        'created_at': evidence.created_at.isoformat(),
    }


@app.get('/organizations/{org_id}/evidence')
async def list_evidence(
    org_id: str,
    project_id: str | None = Query(default=None),
    item_type: str | None = Query(default=None),
    scan_status: str | None = Query(default=None),
    quarantined: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if org_id != ctx.org_id:
        raise HTTPException(status_code=403, detail='Cross-tenant access denied')
    if project_id:
        await _project_for_org(db, project_id, ctx.org_id)

    filters = [EvidenceItem.org_id == ctx.org_id]
    if project_id:
        filters.append(EvidenceItem.project_id == project_id)
    if item_type:
        filters.append(EvidenceItem.item_type == item_type)
    if scan_status:
        filters.append(EvidenceItem.scan_status == scan_status)
    if quarantined is True:
        filters.append(EvidenceItem.scan_status != 'clean')
    if quarantined is False:
        filters.append(EvidenceItem.scan_status == 'clean')

    offset = (page - 1) * page_size
    total = await db.scalar(select(func.count()).select_from(EvidenceItem).where(*filters))
    rows = (
        await db.execute(
            select(EvidenceItem)
            .where(*filters)
            .order_by(EvidenceItem.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()

    items = [
        {
            'id': row.id,
            'org_id': row.org_id,
            'project_id': row.project_id,
            'audit_run_id': row.audit_run_id,
            'integration_id': row.integration_id,
            'item_type': row.item_type,
            'name': row.name,
            'object_key': row.object_key,
            'sha256': row.sha256,
            'scan_status': row.scan_status,
            'quarantine_reason': row.quarantine_reason,
            'metadata_json': row.metadata_json,
            'signature_bundle_json': row.signature_bundle_json,
            'created_at': row.created_at.isoformat(),
        }
        for row in rows
    ]
    return {
        'items': items,
        'page': page,
        'page_size': page_size,
        'total': int(total or 0),
    }


@app.get('/evidence/{evidence_id}/download')
async def download_evidence(
    evidence_id: str,
    ctx: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    evidence = await db.scalar(select(EvidenceItem).where(EvidenceItem.id == evidence_id, EvidenceItem.org_id == ctx.org_id))
    if evidence is None:
        raise HTTPException(status_code=404, detail='Evidence not found')
    if evidence.scan_status != 'clean':
        raise HTTPException(status_code=423, detail='Evidence quarantined')

    store = get_object_store()
    try:
        content = await store.get_bytes(evidence.object_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail='Stored object missing') from exc

    content_type = evidence.metadata_json.get('content_type', 'application/octet-stream')
    headers = {'Content-Disposition': f'attachment; filename="{evidence.name}"'}
    return StreamingResponse(iter([content]), media_type=content_type, headers=headers)


@app.get('/audit-log')
async def list_audit_log(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    ctx: UserContext = Depends(require_roles('org_admin')),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    offset = (page - 1) * page_size
    rows = (
        await db.execute(
            select(AuditLogEntry)
            .where(AuditLogEntry.org_id == ctx.org_id)
            .order_by(AuditLogEntry.id.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()

    data = [
        {
            'id': row.id,
            'org_id': row.org_id,
            'actor_user_id': row.actor_user_id,
            'action': row.action,
            'entity_type': row.entity_type,
            'entity_id': row.entity_id,
            'payload_json': row.payload_json,
            'prev_hash': row.prev_hash,
            'entry_hash': row.entry_hash,
            'created_at': row.created_at.isoformat(),
        }
        for row in rows
    ]
    return {'page': page, 'page_size': page_size, 'items': data}
