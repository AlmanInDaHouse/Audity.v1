# Pre-GA Release Evidence

## Final Status

The three blocking evidence gaps for pre-GA pilot readiness were executed for real and closed:

1. PDF runtime validated in Linux containers
2. live DB/API integration validated without skips
3. browser E2E validated on the real container stack

## Environment Snapshot

- Date: 2026-03-13
- Docker: Linux daemon on Docker Desktop 4.50.0
- Stack services used: `postgres`, `redis`, `minio`, `temporal`, `api`, `worker`, `frontend`, `caddy`
- Database migrations applied: `alembic upgrade head`
- Browser validation entrypoint: `https://localhost:5443`

## Evidence Summary

### 1. PDF Docker/Linux

- `backend/Dockerfile` and `worker/Dockerfile` rechecked
- images built successfully
- WeasyPrint imported successfully in both Linux containers
- real PDFs generated in both containers
- file headers/trailers and sizes verified
- PDFs parsed successfully with `pypdf` for verification
- backend PDF-related tests passed:
  - `test_pdf_generation_has_pdf_header`
  - `test_create_audit_run_happy_path`
  - `test_export_auditor_package_contains_artifacts`

Detailed record: `docs/pdf_runtime_validation.md`

### 2. Real Integration

- live API checked for AI orchestrator removal
- Postgres RLS checked directly
- live RBAC/cross-tenant checks passed
- append-only audit log trigger and hash chain passed
- final result: `4 passed`

Detailed record: `docs/integration_validation.md`

### 3. Browser E2E

- login -> overview -> projects -> open project -> launch audit run -> wait completed -> reports -> PDF download -> AI removal -> enterprise/DPA gate
- final result: `1 passed (22.1s)` on Chromium against `https://localhost:5443`
- screenshots and downloaded PDF stored under `.tmp/release_evidence/e2e/`

Detailed record: `docs/e2e_release_validation.md`

## Bugs Found And Fixed In This Phase

1. `POST /projects/{project_id}/audit-runs` could fail with `500` on the real Postgres/RLS stack.
   - Root cause: post-commit `db.refresh(run)` in a pooled/RLS-backed request path.
   - Fix: remove the refresh/requery path and return the committed ORM object directly.

2. `POST /organizations/{org_id}/projects` failed in real integration with the same class of issue.
   - Root cause: post-commit `db.refresh(project)`.
   - Fix: remove refresh and return the committed object directly.

3. Same fragile pattern existed in:
   - `POST /projects/{project_id}/integrations`
   - `POST /control-catalogs`
   - `POST /projects/{project_id}/evidence/upload`
   - Fix: remove unnecessary post-commit `refresh()` calls.

4. Containerized API stack was running `uvicorn --reload`.
   - Impact: inappropriate for release verification and a source of process churn during validation.
   - Fix: remove `--reload` from the `api` command in `docker-compose.yml`.

5. Playwright release flow was under-specified and not robust enough for the required evidence.
   - Fix: expanded `frontend/tests/e2e/critical-path.spec.ts`, enabled HTTPS-tolerant Playwright config, added artifact capture and stricter release assertions.

## Acceptance Decision

### Acceptance Criteria Outcome

- PDF runtime validated really in Linux/container: PASS
- integration tests executed really with DB/API and no env skips: PASS
- browser E2E executed really on the containerized stack: PASS
- release evidence documentation updated: PASS

## Residual Risk

- Non-blocking warnings remain:
  - FastAPI `@app.on_event` deprecation warnings
  - SQLite test teardown warning about FK cycle ordering in local/unit tests
- E2E release coverage is intentionally focused on the critical pilot path, not a full exploratory browser matrix

## Verdict

Ready for controlled pre-GA pilot based on executed evidence.
