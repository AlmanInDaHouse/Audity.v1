# Integration Validation

## Scope

Real DB/API validation against the live container stack:

- AI orchestrator runtime exposure check
- Postgres RLS enforcement
- live RBAC and cross-tenant isolation
- append-only audit log trigger and hash chain

## Environment

- Date: 2026-03-13
- API endpoint under test: `http://api:8000` from inside the API container
- Database under test: `postgresql+asyncpg://audity:audity@postgres:5432/audity`
- Migrations applied with `alembic upgrade head`
- Postgres role came from `infra/postgres/init/001_app_role.sql`

## Commands Executed

```powershell
docker compose exec -T api uv run alembic upgrade head
docker compose exec -T api sh -lc "cd /workspace/backend && INTEGRATION_BASE_URL=http://api:8000 DATABASE_URL=postgresql+asyncpg://audity:audity@postgres:5432/audity uv run pytest tests_integration/test_ai_runtime_decommissioned.py tests_integration/test_rls_enforcement.py tests_integration/test_postgres_integration.py -vv"
```

## Exact Results

Final rerun on stable stack:

```text
tests_integration/test_ai_runtime_decommissioned.py::test_ai_orchestrator_routes_are_not_exposed PASSED
tests_integration/test_rls_enforcement.py::test_postgres_rls_blocks_cross_tenant_even_without_app_filter PASSED
tests_integration/test_postgres_integration.py::test_tenant_isolation_and_rbac_live_api PASSED
tests_integration/test_postgres_integration.py::test_audit_log_append_only_and_hash_chain_in_postgres PASSED
============================== 4 passed in 11.66s ==============================
```

## Evidence

- `/ai-orchestrator/runs` returns `404` in the live API.
- Direct Postgres query with `app.current_org_id` set to tenant A can read own project and returns `NULL` for tenant B project.
- Tenant A admin cannot read tenant B project, run or evidence through the live API.
- Auditor can launch runs; viewer remains blocked from run launch and evidence upload.
- Postgres trigger `trg_audit_log_no_update` exists and update/delete attempts on `audit_log_entries` raise Postgres errors.
- Hash chain validation returned `0` breaks.

## Bugs Found And Fixed During Integration

1. `POST /projects/{project_id}/audit-runs` could fail in live Postgres/RLS paths because it called `db.refresh(run)` after commit.
   - Root cause: the ORM object was refreshed after commit under pooled Postgres/RLS conditions.
   - Fix: return the already-persisted object directly (`expire_on_commit=False`), removing the fragile refresh path.

2. `POST /organizations/{org_id}/projects` failed in the live integration test for the same reason.
   - Root cause: `db.refresh(project)` after commit under Postgres/RLS.
   - Fix: remove post-commit refresh and return the committed object directly.

3. Same fragile pattern existed in `create_integration`, `create_control_catalog`, and `upload_evidence`.
   - Fix: remove the unnecessary post-commit `refresh()` calls in those creation paths as well.

## Acceptance Criteria

- Runtime does not expose AI orchestrator routes: PASS
- RLS works with real Postgres, not only app-side filters: PASS
- Critical RBAC and audit log guarantees survive on the real stack: PASS
- No skips due to missing DB/API environment: PASS

## Residual Risk

- Integration coverage is focused and release-oriented, not a full system sweep. It proves the blocking pre-GA claims requested here, but does not replace a broader regression suite.
