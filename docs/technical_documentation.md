# Audity — Technical Documentation

## 1. Architecture Overview

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CADDY (HTTPS Proxy)                       │
│                    :443 → frontend / :443/api → API                  │
└────────────────────┬─────────────────────┬──────────────────────────┘
                     │                     │
            ┌────────▼────────┐   ┌────────▼────────┐
            │  FRONTEND       │   │  BACKEND API     │
            │  Next.js :3000  │   │  FastAPI :8000   │
            │  Pages + CSR    │   │  REST + WebSocket│
            └─────────────────┘   └────┬───┬───┬─────┘
                                       │   │   │
                          ┌────────────┘   │   └──────────────┐
                          │                │                  │
                 ┌────────▼─────┐  ┌───────▼──────┐  ┌───────▼──────┐
                 │  PostgreSQL  │  │    Redis      │  │    MinIO     │
                 │  :5432       │  │    :6379      │  │    :9000     │
                 │  RLS enabled │  │  Rate limits  │  │  S3 evidence │
                 └──────────────┘  │  Sessions     │  └──────────────┘
                                   └──────────────┘
                                        │
                 ┌──────────────────────┘
                 │
          ┌──────▼──────┐        ┌──────────────┐
          │  TEMPORAL    │◄──────│  WORKER       │
          │  :7233       │       │  Python       │
          │  Workflows   │       │  Activities   │
          └─────────────┘        └──────────────┘
```

### Core Components

| Component | Technology | Port | Purpose |
|-----------|-----------|------|---------|
| `api` | FastAPI (uvicorn) | 8000 | REST API, auth, RBAC, enterprise endpoints |
| `worker` | Python (Temporal SDK) | — | Async workflow execution (audit runs) |
| `frontend` | Next.js (React) | 3000 | Dashboard, project management, reports |
| `postgres` | PostgreSQL 16 | 5432 | Primary datastore with RLS |
| `redis` | Redis 7 | 6379 | Rate limiting, session cache |
| `minio` | MinIO | 9000 | S3-compatible object store for evidence/reports |
| `temporal` | Temporal Server | 7233 | Workflow orchestration engine |
| `caddy` | Caddy | 443 | HTTPS reverse proxy with auto-certs |

### Docker Compose Profiles

| Profile | Services | When to use |
|---------|----------|-------------|
| (default) | postgres, redis, minio, temporal, api, worker, frontend, caddy | Always |
| `idp` | Keycloak | Enterprise IdP with OIDC/SAML |
| `vault` | HashiCorp Vault | Enterprise secret management |
| `av` | ClamAV | Malware scanning for uploads |
| `obs` | OTel Collector, Prometheus, Grafana, Loki | Full observability stack |
| `backup` | Backup job containers | Recurring Postgres + MinIO backups |
| `waf` | Nginx reverse proxy | WAF rules + security headers |

---

## 2. Data Model

### Core Tables (with org_id FK + RLS)

```
organizations
├── id (PK, UUID)
├── name
├── slug
├── settings_json
└── created_at

users
├── id (PK, UUID)
├── email (unique)
├── name
├── role (Enum: org_admin, auditor, client_viewer)
└── is_active

memberships
├── id (PK, UUID)
├── user_id (FK → users)
├── org_id (FK → organizations)
└── role_override

projects  [RLS ✓]
├── id (PK, UUID)
├── org_id (FK → organizations)
├── name
├── description
├── criticality (Enum: low, medium, high)
├── sensitivity (Enum: public, internal, confidential)
├── tags_json
└── created_at

audit_runs  [RLS ✓]
├── id (PK, UUID)
├── project_id (FK → projects)
├── org_id (FK → organizations)
├── status (Enum: queued, running, completed, failed)
├── risk_score
├── catalog_version
├── report_evidence_id (FK → evidence_items)
├── summary_json
├── signature_bundle_json
└── created_at / updated_at

findings  [RLS ✓]
├── id (PK, UUID)
├── audit_run_id (FK → audit_runs)
├── control_id
├── status (Enum: open, resolved, waived, approved)
├── severity
├── notes
├── evidence_refs_json
└── created_at

evidence_items  [RLS ✓]
├── id (PK, UUID)
├── project_id (FK → projects)
├── org_id (FK → organizations)
├── name
├── item_type
├── storage_ref
├── sha256
├── scan_status (clean / infected / scan_error / pending)
├── manifest_json
├── signature_bundle_json
├── retention_days / immutable / version
├── metadata_json
└── created_at

remediation_tasks  [RLS ✓]
├── id (PK, UUID)
├── finding_id (FK → findings)
├── title / description
├── assignee_user_id (FK → users)
├── status / due_date / sla_due_at
└── created_at
```

### Enterprise Tables
- `integrations` — Project-level connectors (GitHub, Jira, etc.)
- `outbound_integrations` — Org-level outbound connectors
- `scim_tokens` — SCIM bearer token storage
- `role_permissions` — Custom RBAC overrides per org
- `security_policies` — Org-level security settings
- `pricing_plans` — Org-level pricing/feature gating
- `approval_records` — Finding approval workflow
- `remediation_comments` — Discussion on remediation tasks
- `audit_log_entries` — Hash-chain audit log

### Legacy AI Orchestrator Tables

These tables remain in the repository and migration history for backward compatibility only.
They are not exposed by the current pre-GA runtime or frontend.
- `ai_runs` — AI debate workflow runs
- `ai_run_inputs` — Scope, constraints, acceptance criteria
- `ai_agent_outputs` — Per-agent outputs per round
- `ai_patch_candidates` — Proposed code patches
- `ai_guardrail_results` — Lint, test, coverage, security checks
- `ai_decisions` — Final accept/reject/merge decisions

### RLS Policy Model

Every org-scoped table has:
```sql
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <table> FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_<table> ON <table>
  FOR ALL
  USING (org_id = current_setting('app.current_org_id', true)::text)
  WITH CHECK (org_id = current_setting('app.current_org_id', true)::text);
```

Context is set per request:
```python
# app/tenancy.py
async def set_current_org(session: AsyncSession, org_id: str):
    await session.execute(text(
        "SELECT set_config('app.current_org_id', :org_id, false)"
    ), {"org_id": org_id})
```

App role `audity` has `NOBYPASSRLS` to ensure policies are enforced even for the app connection.

---

## 3. Security Architecture

### Authentication

| Method | Endpoint | Usage |
|--------|----------|-------|
| Mock login (dev only) | `POST /auth/mock/login` | Issues JWT + refresh token for seeded demo users |
| OIDC (enterprise) | Keycloak profile | JWKS-validated tokens with issuer/audience checks |
| Refresh rotation | `POST /auth/refresh` | Rotates refresh token, issues new access token |
| Logout | `POST /auth/logout` | Revokes refresh session |

JWT tokens are RS256-signed. JWKS endpoint at `/auth/.well-known/jwks.json`.

Claims:
```json
{
  "sub": "<user_id>",
  "email": "<email>",
  "org_id": "<org_id>",
  "role": "auditor",
  "mfa": true,
  "exp": 1740000000
}
```

### Authorization (RBAC + ABAC)

**Roles**: `org_admin`, `auditor`, `client_viewer`

Default permissions:
| Action | org_admin | auditor | client_viewer |
|--------|-----------|---------|---------------|
| project:create | ✅ | ✅ | ❌ |
| project:delete | ✅ | ❌ | ❌ |
| evidence:upload | ✅ | ✅ | ❌ |
| audit:run | ✅ | ✅ | ❌ |
| finding:approve | ✅ | ❌ | ❌ |
| report:download | ✅ | ✅ | ✅ |
| enterprise:manage | ✅ | ❌ | ❌ |

**ABAC**: Project-level attributes (`sensitivity`, `criticality`) can deny access even for permitted roles. Example: `client_viewer` denied for `confidential` projects.

### Secret Management

```
┌──────────┐     ┌──────────────────┐     ┌──────────┐
│  API     │────▶│  SecretStore     │────▶│  Backend │
│ endpoint │     │  (abstraction)   │     │          │
└──────────┘     └────┬────────┬────┘     └──────────┘
                      │        │
              ┌───────▼──┐  ┌──▼─────────┐
              │ env store │  │ Vault store│
              │ (AES-GCM) │  │ (transit)  │
              └───────────┘  └────────────┘
```

- DB stores `secret_ref` (UUID), never plaintext.
- `env` backend: AES-GCM encryption with `secret_encryption_key`.
- `vault` backend: HashiCorp Vault KV v2.
- Plaintext detection: API blocks `token`, `password`, `secret`, `private_key` in `config_json` fields.

### Evidence Signing

- Algorithm: Ed25519
- Flow: `SHA-256(content)` → `Ed25519.sign(manifest_hash)` → bundle stored in DB
- Verification endpoint: `GET /evidence/{id}/verify-signature`
- TSA: Stub (RFC 3161 TODO)

### Audit Log

- Append-only with hash chain (`SHA-256(prev_hash + entry)`).
- Records: action, user, org, resource_type, resource_id, detail_json, timestamp.
- Tamper detection: any break in chain invalidates subsequent entries.

### Upload Security

1. MIME allowlist validation
2. Size check against org pricing plan limit
3. SHA-256 computed on storage write
4. ClamAV scan (if `feature_upload_av_scan=true`)
5. `scan_status` gates download (`423 Locked` for infected/error)

---

## 4. Temporal Workflows

### Audit Run Workflow

```
┌─────────────────────────────────────────────────────┐
│               AuditRunWorkflow                       │
│                                                      │
│  1. collect_evidence_activity                        │
│     └─ Fetch from GitHub, Google Workspace, manual   │
│        Input: project integrations config            │
│        Output: evidence items list                   │
│                                                      │
│  2. evaluate_controls_activity                       │
│     └─ AI (LLM) + heuristic fallback per control    │
│        Input: evidence + catalog controls            │
│        Output: findings with severity/status         │
│                                                      │
│  3. calculate_risk_activity                          │
│     └─ Weighted score from findings                  │
│        Input: findings list                          │
│        Output: risk_score (0-100)                    │
│                                                      │
│  4. generate_report_activity                         │
│     └─ HTML + PDF + sign + store in MinIO            │
│        Input: run data + findings                    │
│        Output: report_evidence_id                    │
│                                                      │
│  5. persist_results_activity                         │
│     └─ Save to DB, update run status                 │
│        Input: all results                            │
│        Output: completed run                         │
└─────────────────────────────────────────────────────┘
```

### Legacy AI Orchestrator Debate Workflow

Historical design only. The active product runtime uses the local-first audit workflow and `knowledge_engine`.

```
┌─────────────────────────────────────────────────────┐
│               DebateWorkflow                         │
│                                                      │
│  1. prepare_repo_snapshot                            │
│     └─ Snapshot working branch / commit              │
│        Timeout: 5 min                                │
│                                                      │
│  2. run_claude_auditor                               │
│     └─ Static audit review (currently stub)          │
│        Timeout: 15 min                               │
│                                                      │
│  3. run_codex_implementer                            │
│     └─ Generate patch plan (currently stub)          │
│        Timeout: 20 min                               │
│                                                      │
│  4. run_gemini_arbiter                               │
│     └─ Decide: accept_claude / accept_codex / merge  │
│        Timeout: 10 min                               │
│                                                      │
│  5. execute_with_guardrails                          │
│     └─ Lint, test, coverage, security checks         │
│        Timeout: 30 min                               │
└─────────────────────────────────────────────────────┘
```

### Temporal Configuration

- Task queue: `audit-tasks` (audit runs)
- Retry policy: configured in activity decorators
- Worker concurrency: tunable via `TEMPORAL_WORKER_CONCURRENCY`
- Server: `temporal:7233` (Docker), configurable via `TEMPORAL_SERVER`

---

## 5. Catalogs and Controls

### Structure

```
catalogs/
├── iso27001_annex_a.v1.yml    # ISO 27001 Annex A controls
├── ens_measures.v1.yml        # ENS (Spain) measures
├── rgpd_checklist.v1.yml      # GDPR checklist
└── control_mapping.v1.yml     # Cross-framework mapping
```

### Control Schema (YAML)

```yaml
- id: "ISO-A.5.1"
  title: "Policies for information security"
  description: "Management direction for information security..."
  tags: ["governance", "policy"]
  level: "organizational"
  severity: "high"
  mapped_controls: ["ENS-ORG.1"]
  evidence_requirements:
    - "information_security_policy"
  evaluator_key: "manual_evidence"
```

### Versioning

- Catalogs versioned in filename: `iso27001_annex_a.v1.yml`
- `catalog_engine.py` computes SHA-256 checksum per catalog load.
- `catalog_version` stored per audit run for reproducibility.

### Evaluators

| Key | Implementation | Source |
|-----|---------------|--------|
| `manual_evidence` | Checks for presence of uploaded evidence | `rules.py` |
| `github_repo_check` | GitHub API for repo settings (branches, protection) | `rules.py` |
| `gworkspace_check` | Google Workspace API for user/MFA settings | `rules.py` |
| `knowledge_engine` | Local-first evidence evaluation and structured heuristics | `knowledge_engine.py` |
| (support) | Deterministic keyword and metadata matching | `knowledge_engine.py` |

---

## 6. API Reference (Key Endpoints)

### Auth

```bash
# Login (dev/demo)
curl -X POST https://localhost:5443/api/auth/mock/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@demo.local", "org_id": "<org_id>", "mfa": true}'

# Refresh token
curl -X POST https://localhost:5443/api/auth/refresh \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'

# Logout
curl -X POST https://localhost:5443/api/auth/logout \
  -H "Authorization: Bearer <access_token>"
```

### Projects

```bash
# List projects
curl https://localhost:5443/api/organizations/<org_id>/projects \
  -H "Authorization: Bearer <token>"

# Create project
curl -X POST https://localhost:5443/api/organizations/<org_id>/projects \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Infra Audit", "description": "...", "criticality": "high"}'

# Get project
curl https://localhost:5443/api/projects/<project_id> \
  -H "Authorization: Bearer <token>"
```

### Audit Runs

```bash
# Launch audit run (1-click)
curl -X POST https://localhost:5443/api/projects/<project_id>/audit-runs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"catalog_version": "v1"}'

# Get run with findings
curl https://localhost:5443/api/projects/<project_id>/audit-runs/<run_id> \
  -H "Authorization: Bearer <token>"

# List findings
curl https://localhost:5443/api/projects/<project_id>/audit-runs/<run_id>/findings \
  -H "Authorization: Bearer <token>"
```

### Evidence

```bash
# Upload evidence
curl -X POST https://localhost:5443/api/projects/<project_id>/evidence/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@policy.pdf" \
  -F "item_type=manual_upload" \
  -F 'metadata_json={"source": "manual"}'

# Download evidence
curl https://localhost:5443/api/evidence/<evidence_id>/download \
  -H "Authorization: Bearer <token>" --output file.pdf

# Verify signature
curl https://localhost:5443/api/evidence/<evidence_id>/verify-signature \
  -H "Authorization: Bearer <token>"
```

### Enterprise

```bash
# Get feature flags
curl https://localhost:5443/api/enterprise/features \
  -H "Authorization: Bearer <token>"

# Update feature flags
curl -X PUT https://localhost:5443/api/enterprise/features \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"feature_signing": true, "feature_rbac_abac": true}'

# Export auditor package
curl https://localhost:5443/api/projects/<project_id>/audit-runs/<run_id>/export/package \
  -H "Authorization: Bearer <token>" --output audit-package.zip
```

---

## 7. Frontend Architecture

### Route Map

| Route | Page | Auth Required | RBAC |
|-------|------|---------------|------|
| `/` | Marketing landing | No | — |
| `/login` | Demo login | No | — |
| `/overview` | Org dashboard | Yes | All roles |
| `/projects` | Project listing | Yes | All roles |
| `/projects/[id]` | Project detail (6 tabs) | Yes | Varies by tab |
| `/projects/new` | Create project | Yes | org_admin, auditor |
| `/audit-runs` | Cross-project runs | Yes | All roles |
| `/evidence` | Evidence library | Yes | All roles |
| `/reports` | Report listing + download | Yes | All roles |
| `/enterprise` | Feature flags + pricing | Yes | org_admin only |
| `/integrations` | Outbound connectors | Yes | org_admin only |

### Components

| Component | File | Purpose |
|-----------|------|---------|
| `AppShell` | `components/app-shell.tsx` | Sidebar nav + header + content |
| `SessionContext` | `components/session-context.tsx` | Auth state management |
| `ToastProvider` | `components/toast-provider.tsx` | Toast notification system |
| `Pagination` | `components/pagination.tsx` | Table pagination |
| `StatusBadge` | `components/status-badge.tsx` | Color-coded status pills |
| `Breadcrumbs` | `components/breadcrumbs.tsx` | Navigation breadcrumbs |
| `ConfirmDialog` | `components/confirm-dialog.tsx` | Dangerous action confirmation |
| `AppShell` | `components/app-shell.tsx` | Global navigation shell and auth-aware layout |

### Feature Flags in Frontend

The frontend fetches `GET /enterprise/features` and conditionally renders:
- Signature verify buttons (`feature_signing`)
- Enterprise IdP notice on login (`feature_auth_enterprise`)
- Pricing plan management
- AV scan status badges

### Known Frontend Issues

1. **No auth guard middleware**: Pages don't redirect to `/login` if session is missing; they just render empty.
2. **N+1 API queries**: `audit-runs`, `reports`, and `projects` pages fetch runs per-project individually.
3. **`pushToast` in useEffect deps**: Can cause unnecessary re-renders if toast function identity changes.
4. **803-line project detail page**: Should be split into sub-components per tab.
5. **No error boundary**: Uncaught errors crash entire page without recovery.

---

## 8. Observability

### Metrics (Prometheus)

Available at `GET /metrics`:

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total requests by method, path, status |
| `http_request_duration_seconds` | Histogram | Request latency (p50, p95, p99) |
| `rate_limit_hits_total` | Counter | Rate limit rejections |
| `quarantined_uploads_total` | Counter | AV-quarantined uploads |
| `audit_runs_total` | Counter | Audit runs by status |

### Tracing (OpenTelemetry)

- Enabled via `OTEL_EXPORTER_OTLP_ENDPOINT` env var.
- Instruments: FastAPI requests, SQLAlchemy queries.
- Exporter: OTLP gRPC to OTel Collector.

### Dashboards (Grafana)

Pre-configured in `infra/observability/grafana/`:
- API latency p95 over time
- Rate limit hit rate
- Quarantined upload count
- Audit run completion rate

### Logging (Loki)

- Structured JSON logs from API and worker.
- Collected by Loki via OTel Collector.
- Queryable in Grafana Explore.

---

## 9. Backup and Restore

### Procedures

**Backup:**
```bash
# PowerShell
scripts/backup.ps1

# Bash
scripts/backup.sh
```
Creates timestamped dumps in `/backups/`:
- `postgres_<timestamp>.sql.gz` — Full PostgreSQL dump
- `minio_<timestamp>.tar.gz` — MinIO data tarball

**Restore:**
```bash
# PowerShell
scripts/restore.ps1 <backup_timestamp>

# Bash
scripts/restore.sh <backup_timestamp>
```

### RTO/RPO Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| RPO (Recovery Point Objective) | ≤ 24h | Daily backup job in `backup` profile |
| RTO (Recovery Time Objective) | ≤ 2h | Restore script + DB migration + smoke test |

### Automated Backup

`docker compose --profile backup up -d` enables recurring backup containers that run daily.

---

## 10. Operational Runbooks

### Incident: API Unresponsive

1. Check health: `curl https://localhost:5443/api/health`
2. Check logs: `docker compose logs api --tail=200`
3. Check dependencies: `docker compose ps` for postgres, redis, minio
4. If DB down: `docker compose restart postgres` → wait for healthcheck → restart api
5. If Redis down: API falls back to in-memory rate limiter → restart redis
6. Escalate if persistent: check disk space, memory, connection pool exhaustion

### Incident: Audit Run Stuck in "queued"

1. Check Temporal UI: `http://localhost:8080` → search workflow by ID
2. If no workflow found: api failed before starting → check api logs
3. If workflow failed: check worker logs → `docker compose logs worker --tail=100`
4. Retry: terminate stuck workflow in Temporal UI → re-trigger audit run from frontend

### Incident: Evidence Quarantined

1. Download blocked with HTTP 423 → evidence flagged by ClamAV
2. Check `evidence_items.scan_status` in DB
3. If false positive: update `scan_status = 'clean'` via direct DB update (admin only)
4. If true positive: notify user, do NOT change status

### Incident: Cross-Tenant Data Visible

1. **CRITICAL**: Stop accepting traffic immediately
2. Identify query: check audit log for cross-org access patterns
3. Verify RLS: `SELECT * FROM pg_policies` for affected table
4. Check `set_current_org` was called: search api logs for org_id context
5. Fix and deploy hotfix
6. Notify affected tenants per DPA obligations

---

## 11. Deployment Guide

### Development (Local)

```bash
# Start all services
scripts/dev_up.ps1   # or dev_up.sh

# Run migrations
docker compose exec api uv run alembic upgrade head

# Seed demo data
docker compose exec api uv run python -m app.scripts.seed_data

# Run tests
scripts/dev_test.ps1   # or dev_test.sh
```

### Staging

```bash
# Use .env.staging with real credentials
cp .env.staging .env

# Start with enterprise profiles
docker compose --profile idp --profile vault --profile av --profile obs up -d

# Migrate
docker compose exec -T api uv run alembic upgrade head

# Smoke test
docker compose exec -T api uv run python -m app.scripts.demo_audit
```

### Production

```bash
# Use .env.production (NEVER commit this)
# Required overrides:
#   SECRET_ENCRYPTION_KEY=<random 32-byte hex>
#   VAULT_TOKEN=<real vault token>
#   DATABASE_URL=<production postgres URL>
#   REDIS_URL=redis://:password@redis:6379/0
#   MINIO_ROOT_USER=<production credentials>
#   MINIO_ROOT_PASSWORD=<production credentials>
#   APP_ENV=production
#   STORAGE_BACKEND=s3
#   WORKFLOW_MODE=temporal

docker compose --profile backup --profile av up -d
docker compose exec -T api uv run alembic upgrade head
```

### Environment Variables Reference

| Variable | Default | Required in Prod | Description |
|----------|---------|-----------------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./audity.db` | ✅ | Postgres connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | ✅ | Redis with AUTH |
| `SECRET_ENCRYPTION_KEY` | `(empty)` | ✅ | AES-GCM key for secrets |
| `STORAGE_BACKEND` | `memory` | ✅ (must be `s3`) | Evidence storage backend |
| `APP_ENV` | `dev` | ✅ (must be `production`) | Environment mode |
| `WORKFLOW_MODE` | `inline` | ✅ (must be `temporal`) | Workflow execution mode |
| `OIDC_JWKS_URL` | (empty) | For SSO | JWKS endpoint URL |
| `OIDC_ISSUER` | `http://localhost:8000` | For SSO | Token issuer |
| `VAULT_ADDR` | `http://vault:8200` | For Vault | Vault server address |
| `VAULT_TOKEN` | (empty) | For Vault | Vault access token |
| `CLAMAV_HOST` | `clamav` | For AV | ClamAV service hostname |
| `OPENAI_API_KEY` | (empty) | For AI | LLM API key |
| `TEMPORAL_SERVER` | `temporal:7233` | ✅ | Temporal gRPC address |
