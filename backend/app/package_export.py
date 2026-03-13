from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import get_settings
from app.models import AuditRun, EvidenceItem, Finding, Project, RemediationTask
from app.storage import get_object_store

try:
    from weasyprint import HTML
except Exception:
    HTML = None


@dataclass
class ExecutiveReportArtifact:
    html: str
    pdf: bytes
    context: dict[str, Any]


def _report_environment() -> Environment:
    template_dir = Path(__file__).resolve().parent / 'templates'
    return Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml']),
    )


def _render_pdf(html: str) -> bytes:
    settings = get_settings()
    engine = settings.report_pdf_engine.lower()
    if engine == 'weasyprint' and HTML is not None:
        return HTML(string=html).write_pdf()
    if engine in {'typst', 'playwright'}:
        raise RuntimeError(f'Unsupported report PDF engine: {engine}. Pre-GA runtime supports only weasyprint.')
    if HTML is None:
        raise RuntimeError('WeasyPrint runtime is unavailable. Install production PDF dependencies before generating reports.')
    return HTML(string=html).write_pdf()


def build_executive_report(
    *,
    org_id: str,
    project_name: str,
    audit_run_id: str,
    risk_score: float | None,
    risk_level: str | None,
    findings: list[dict[str, Any]],
    remediation_tasks: list[dict[str, Any]],
    evidence_summary: dict[str, Any],
) -> ExecutiveReportArtifact:
    settings = get_settings()
    context = {
        'brand_name': settings.report_brand_name,
        'support_email': settings.report_support_email,
        'generated_at': datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC'),
        'org_id': org_id,
        'project_name': project_name,
        'audit_run_id': audit_run_id,
        'risk_score': risk_score,
        'risk_level': risk_level or 'unknown',
        'findings': findings,
        'remediation_tasks': remediation_tasks,
        'evidence_summary': evidence_summary,
        'findings_total': len(findings),
        'critical_findings': len([item for item in findings if item.get('severity') == 'high']),
        'priority_actions': remediation_tasks[:5],
    }
    html = _report_environment().get_template('executive_report.html.j2').render(**context)
    pdf = _render_pdf(html)
    return ExecutiveReportArtifact(html=html, pdf=pdf, context=context)


async def build_auditor_package(
    *,
    org_id: str,
    project: Project,
    run: AuditRun,
    findings: list[Finding],
    tasks: list[RemediationTask],
    evidence_items: list[EvidenceItem],
) -> bytes:
    store = get_object_store()
    output = io.BytesIO()
    executive_artifact = build_executive_report(
        org_id=org_id,
        project_name=project.name,
        audit_run_id=run.id,
        risk_score=run.risk_score,
        risk_level=run.risk_level,
        findings=[
            {
                'id': f.id,
                'control_id': f.control_id,
                'title': f.title,
                'severity': f.severity.value,
                'result': f.result.value,
                'notes': f.notes,
            }
            for f in findings
        ],
        remediation_tasks=[
            {
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'status': t.status,
                'due_date': t.due_date.isoformat() if t.due_date else None,
            }
            for t in tasks
        ],
        evidence_summary={'items': len(evidence_items)},
    )
    with zipfile.ZipFile(output, mode='w', compression=zipfile.ZIP_DEFLATED) as archive:
        manifest = {
            'generated_at': datetime.now(UTC).isoformat(),
            'org_id': org_id,
            'project_id': project.id,
            'project_name': project.name,
            'audit_run_id': run.id,
            'risk_score': run.risk_score,
            'risk_level': run.risk_level,
            'evidence_count': len(evidence_items),
        }
        archive.writestr('manifest.json', json.dumps(manifest, indent=2))
        archive.writestr('executive-report.html', executive_artifact.html)
        archive.writestr('executive-report.pdf', executive_artifact.pdf)
        archive.writestr(
            'findings.json',
            json.dumps(
                [
                    {
                        'id': f.id,
                        'control_id': f.control_id,
                        'result': f.result.value,
                        'severity': f.severity.value,
                        'notes': f.notes,
                        'signature_bundle': f'{f.id}.json',
                    }
                    for f in findings
                ],
                indent=2,
            ),
        )
        archive.writestr(
            'remediation_tasks.json',
            json.dumps(
                [
                    {
                        'id': t.id,
                        'finding_id': t.finding_id,
                        'title': t.title,
                        'description': t.description,
                        'status': t.status,
                        'due_date': t.due_date.isoformat() if t.due_date else None,
                    }
                    for t in tasks
                ],
                indent=2,
            ),
        )
        for evidence in evidence_items:
            archive.writestr(
                f'signatures/{evidence.id}.json',
                json.dumps(evidence.signature_bundle_json or {}, indent=2),
            )
            archive.writestr(
                f'evidence-metadata/{evidence.id}.json',
                json.dumps(
                    {
                        'id': evidence.id,
                        'name': evidence.name,
                        'sha256': evidence.sha256,
                        'metadata': evidence.metadata_json,
                        'scan_status': evidence.scan_status,
                    },
                    indent=2,
                ),
            )
            try:
                content = await store.get_bytes(evidence.object_key)
                archive.writestr(f'evidence/{evidence.name}', content)
            except Exception:
                archive.writestr(f'evidence/{evidence.name}.missing.txt', 'Object unavailable in store')
    return output.getvalue()
