# PDF Runtime Validation

## Scope

Real validation of the PDF runtime in Linux containers for:

- `backend/Dockerfile`
- `worker/Dockerfile`
- WeasyPrint import/runtime
- real PDF generation
- backend tests that exercise reporting, audit run PDF output and auditor package export

## Environment

- Date: 2026-03-13
- Host: Windows 11 + Docker Desktop 4.50.0
- Container runtime: Linux amd64
- API image base: `python:3.12-slim`
- Worker image base: `python:3.12-slim`
- Critical package verified in both Dockerfiles: `libharfbuzz-subset0`

## Commands Executed

```powershell
docker version
docker compose build api worker frontend
docker compose up -d postgres redis minio temporal api worker frontend caddy
docker compose exec -T api uv run alembic upgrade head
docker compose exec -T api sh -lc "cd /workspace/backend && uv run python - <<'PY'
from pathlib import Path
from app.reporting import HTML, render_report_html, render_report_pdf
assert HTML is not None
html = render_report_html({
    'audit_run_id': 'docker-api-run',
    'project_name': 'Docker API Project',
    'org_name': 'Audity',
    'risk_score': 37,
    'risk_level': 'medium',
    'total_controls': 36,
    'findings': [{'control_id': 'A.5.1', 'title': 'Policy missing', 'severity': 'high', 'status': 'open'}],
    'remediation_tasks': [{'title': 'Publish security policy', 'owner': 'Security', 'status': 'open'}],
})
pdf = render_report_pdf(html)
out = Path('/workspace/.tmp/release_evidence/api-report.pdf')
out.write_bytes(pdf)
print(f'API_WEASYPRINT_IMPORT=ok')
print(f'API_PDF_PATH={out}')
print(f'API_PDF_BYTES={len(pdf)}')
print(f'API_PDF_HEADER={pdf[:8]!r}')
print(f'API_PDF_TRAILER={pdf[-16:]!r}')
PY"
docker compose exec -T worker sh -lc "cd /workspace/worker && uv run python - <<'PY'
from pathlib import Path
from app.reporting import HTML, render_report_html, render_report_pdf
assert HTML is not None
html = render_report_html({
    'audit_run_id': 'docker-worker-run',
    'project_name': 'Docker Worker Project',
    'org_name': 'Audity',
    'risk_score': 18,
    'risk_level': 'low',
    'total_controls': 36,
    'findings': [{'control_id': 'A.5.7', 'title': 'Review cadence set', 'severity': 'low', 'status': 'closed'}],
    'remediation_tasks': [{'title': 'Keep monthly review', 'owner': 'GRC', 'status': 'done'}],
})
pdf = render_report_pdf(html)
out = Path('/workspace/.tmp/release_evidence/worker-report.pdf')
out.write_bytes(pdf)
print(f'WORKER_WEASYPRINT_IMPORT=ok')
print(f'WORKER_PDF_PATH={out}')
print(f'WORKER_PDF_BYTES={len(pdf)}')
print(f'WORKER_PDF_HEADER={pdf[:8]!r}')
print(f'WORKER_PDF_TRAILER={pdf[-16:]!r}')
PY"
docker compose exec -T api sh -lc "python -m pip install --quiet pypdf && cd /workspace && python - <<'PY'
from pathlib import Path
from pypdf import PdfReader
for name in ['api-report.pdf', 'worker-report.pdf']:
    path = Path('/workspace/.tmp/release_evidence') / name
    reader = PdfReader(str(path))
    print(f'{name}: pages={len(reader.pages)} encrypted={reader.is_encrypted}')
PY"
docker compose exec -T api uv run pytest tests/test_reporting.py tests/test_audit_run.py tests/test_enterprise_features.py -k "pdf_generation_has_pdf_header or create_audit_run_happy_path or export_auditor_package_contains_artifacts" -vv
```

## Exact Results

### Docker build

- `audity-api  Built`
- `audity-worker  Built`

### API container PDF generation

```text
API_WEASYPRINT_IMPORT=ok
API_PDF_PATH=/workspace/.tmp/release_evidence/api-report.pdf
API_PDF_BYTES=11722
API_PDF_HEADER=b'%PDF-1.7'
API_PDF_TRAILER=b'ref\n11480\n%%EOF\n'
```

### Worker container PDF generation

```text
WORKER_WEASYPRINT_IMPORT=ok
WORKER_PDF_PATH=/workspace/.tmp/release_evidence/worker-report.pdf
WORKER_PDF_BYTES=11977
WORKER_PDF_HEADER=b'%PDF-1.7'
WORKER_PDF_TRAILER=b'ref\n11734\n%%EOF\n'
```

### Parser validation

```text
api-report.pdf: pages=1 encrypted=False
worker-report.pdf: pages=1 encrypted=False
```

### Backend tests in Linux container

```text
tests/test_reporting.py::test_pdf_generation_has_pdf_header PASSED
tests/test_audit_run.py::test_create_audit_run_happy_path PASSED
tests/test_enterprise_features.py::test_export_auditor_package_contains_artifacts PASSED
================= 3 passed, 5 deselected =================
```

## Artifacts

- `.tmp/release_evidence/api-report.pdf`
- `.tmp/release_evidence/worker-report.pdf`

SHA256:

- `api-report.pdf`: `6EAD7EC356680A1D18CBA0527ACAFCF82CB9A064E92F5AC6FB917C01C6B08C0B`
- `worker-report.pdf`: `7042BE221AAD804EDD1B26E22D1AD77C6FC94A2EAADDFAAFF9323ADC1B1378F4`

## Acceptance Criteria

- WeasyPrint imports in backend and worker Linux containers: PASS
- Real PDFs generated in both containers: PASS
- Files start with `%PDF`, end with `%%EOF`, are non-trivial in size and parse as 1-page PDFs: PASS
- Audit run flow no longer fails for missing PDF runtime: PASS
- Auditor package export still produces downloadable artifacts: PASS

## Residual Risk

- PDF validity parser (`pypdf`) was installed ad hoc inside the running API container for verification only. The product runtime itself still depends on WeasyPrint, which was the component under validation and passed.
