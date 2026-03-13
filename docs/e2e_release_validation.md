# E2E Release Validation

## Scope

Browser E2E executed against the real container stack behind Caddy TLS, covering:

1. login
2. overview
3. projects
4. open project
5. launch audit run
6. wait for result
7. reports
8. download and verify real PDF
9. confirm AI orchestrator is absent from UI/runtime
10. confirm enterprise/DPA gate coherence

## Environment

- Date: 2026-03-13
- Browser runner: Playwright Chromium
- Base URL: `https://localhost:5443`
- TLS mode: internal Caddy certificate, Playwright configured with `ignoreHTTPSErrors: true`
- Demo org reset before each run to keep DPA assertions reproducible

## Commands Executed

```powershell
docker compose exec -T api sh -lc "cd /workspace/backend && uv run python -m app.scripts.seed_data"
docker compose exec -T api sh -lc "cd /workspace/backend && uv run python - <<'PY'
from app.db import SessionLocal
from app.models import Organization
import asyncio
TARGET_ID = 'b079080a-acbd-447a-bd4a-15768525bd20'
async def main():
    async with SessionLocal() as db:
        org = await db.get(Organization, TARGET_ID)
        org.dpa_status = 'pending'
        org.dpa_reference = None
        org.dpa_signed_at = None
        org.onboarding_status = 'pending_dpa'
        org.onboarding_completed_at = None
        await db.commit()
        print(f'DPA_RESET_OK {org.id} {org.dpa_status} {org.onboarding_status}')
asyncio.run(main())
PY"
$env:E2E_BASE_URL='https://localhost:5443'
npx playwright install chromium
npx playwright test tests/e2e/critical-path.spec.ts --project=chromium
```

## Exact Result

Final rerun on stable stack:

```text
DPA_RESET_OK b079080a-acbd-447a-bd4a-15768525bd20 pending pending_dpa

Running 1 test using 1 worker
  ok 1 [chromium] › tests\e2e\critical-path.spec.ts:15:7 › Release critical path › login, audit run, reports PDF, AI removal and DPA gate (18.5s)

  1 passed (22.1s)
```

## Functional Evidence

The passing spec performed all required release steps:

- logged in as `admin@demo.local`
- loaded overview and observed `DPA pendiente`
- opened `Demo Project`
- launched a real audit run from the project page
- waited until the run reached `completed`
- downloaded a real PDF from the run detail page
- loaded `Reports` and confirmed PDF actions are present there
- confirmed `AI Orchestrator` is absent from the UI
- executed a browser-side authenticated `fetch('/api/ai-orchestrator/runs')` and asserted `404`
- loaded `Enterprise Settings`
- confirmed onboarding is blocked while DPA is pending
- registered signed DPA
- completed onboarding
- returned to overview and confirmed `DPA firmado`

## Artifacts

Screenshots:

- `.tmp/release_evidence/e2e/01-overview.png`
- `.tmp/release_evidence/e2e/02-project.png`
- `.tmp/release_evidence/e2e/03-run-completed.png`
- `.tmp/release_evidence/e2e/04-reports.png`
- `.tmp/release_evidence/e2e/05-enterprise.png`
- `.tmp/release_evidence/e2e/06-overview-post-dpa.png`

Downloaded PDF:

- `.tmp/release_evidence/e2e/audit-report-e2e.pdf`
- size: `29627` bytes
- SHA256: `4090ABE29EFD6E358AC34FADE82AC9779798754AE6924AEC87EC95282125DB01`

Playwright outputs:

- `frontend/playwright-report/`
- `frontend/test-results/`

## Acceptance Criteria

- Browser flow runs against the real container stack: PASS
- Real PDF download occurs in browser flow: PASS
- AI orchestrator is not exposed in UI nor runtime route: PASS
- Enterprise/DPA gate stays coherent through pending -> signed -> completed flow: PASS

## Residual Risk

- E2E evidence covers the required release path in Chromium only. It does not claim multi-browser parity.
