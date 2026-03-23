# Audity

Audity es un SaaS B2B multi-tenant de auditoria y compliance para consultoria y equipos internos. En esta fase el producto queda cerrado como plataforma de auditoria con:

- audit runs reproducibles con snapshot de catalogo y trazabilidad;
- multi-tenancy con RLS en PostgreSQL;
- evidencia y reporting firmados;
- modulo de riesgo formal separado del `control posture` de los audit runs;
- monolito FastAPI + frontend Next.js mantenido de forma deliberada.

## Estado de fase

La fase actual queda orientada a salida pre-GA controlada:

- PR1: snapshot de scope y `control_posture_score` persistido.
- PR2: `audit_runs` ligados a `catalog_version` persistida.
- PR3A: modulo `risk` separado con CRUD formal basico.
- PR3B: motor `deterministic-v1`, evaluaciones versionadas, treatments y traceability.

Referencias de estado:

- [Architecture](docs/architecture.md)
- [Technical Documentation](docs/technical_documentation.md)
- [Runbook](docs/runbook.md)
- [Final Market Closure Report](docs/final_market_closure_report.md)
- [PR3B Postgres Release Check](docs/pr3b_postgres_release_check.md)
- [Final Gap Analysis](docs/final_gap_analysis.md)
- [CHANGELOG](CHANGELOG.md)

## Principios de producto cerrados

- No mezclar `control posture` con riesgo formal.
- No usar IA para el calculo formal de riesgo.
- No reescribir el monolito actual.
- Mantener reproducibilidad, trazabilidad y aislamiento multi-tenant.

## Estructura

- `backend/`: FastAPI, modelos, migraciones, workflows y reporting.
- `frontend/`: Next.js UI para portfolio, proyectos, risk, evidence y enterprise.
- `worker/`: worker Temporal.
- `docs/`: documentacion tecnica, operativa y de release.
- `infra/`: compose, helm y perfiles auxiliares.

## Arranque local

PowerShell:

```powershell
.\scripts\dev_up.ps1
.\scripts\dev_test.ps1
```

Bash:

```bash
./scripts/dev_up.sh
./scripts/dev_test.sh
```

Para smoke funcional y datos demo, ver [docs/runbook.md](docs/runbook.md).
