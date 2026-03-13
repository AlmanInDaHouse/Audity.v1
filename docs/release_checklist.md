# Audity — Release Checklist

## Definition of Done

Un release se considera "done" cuando todos los items de la fase correspondiente están marcados `[x]`.

---

## Pre-Release

### CI / Quality Gates
- [ ] `uv run ruff check app tests tests_integration` — 0 errors
- [ ] `uv run mypy app --ignore-missing-imports` — 0 errors (o baseline documentado)
- [ ] `uv run pytest tests/ -q` — all passed
- [ ] `uv run pytest tests_integration/ -q` — all passed (requiere Postgres)
- [ ] `uv run python -m app.scripts.demo_audit` — completa sin errores
- [ ] Frontend `npm run build` — 0 errores de compilación
- [ ] Frontend `npm run lint` — 0 warnings (o baseline)

### Backup / Restore Smoke
- [ ] Ejecutar `scripts/backup.sh` (o `.ps1`) — dump creado en `/backups/`
- [ ] Drop database → ejecutar `scripts/restore.sh` — datos restaurados
- [ ] Verificar que un audit run previo sigue visible post-restore
- [ ] MinIO evidencia accesible post-restore

### Load Test Mínimo
- [ ] `k6 run scripts/load_test.js` — 0 errores en p95 < 2s para endpoints core
- [ ] Rate limiting activo — verificar HTTP 429 para bursts
- [ ] Verificar que Temporal worker procesa audit run bajo carga

### Security / Pentest Checklist
- [ ] `secret_encryption_key` ≠ `dev-only-key-change-me` en producción
- [ ] `vault_token` ≠ `root` en producción
- [ ] Mock login endpoint desactivado o gated a `APP_ENV=dev`
- [ ] CORS origins configurado (no `*` en producción)
- [ ] Redis con AUTH habilitado
- [ ] MinIO credentials ≠ minioadmin/minioadmin
- [ ] Postgres password ≠ postgres/audity para producción
- [ ] `Content-Disposition` filenames sanitizados
- [ ] CSP policy revisada para frontend origin real
- [ ] ClamAV activo si `feature_upload_av_scan=true`
- [ ] Revisar `docs/pentest_runbook.md` y ejecutar items aplicables

### Database / Migrations
- [ ] `alembic upgrade head` en clean database — success
- [ ] `alembic upgrade head` en existing database (idempotent) — success
- [ ] RLS policies activas: `SELECT * FROM pg_policies` muestra policies en todas las tablas tenant
- [ ] App role: `SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname='audity'` → `f, f`

---

## Release

### Versionado
- [ ] Version tag en git: `v0.x.y` con semver
- [ ] CHANGELOG.md actualizado con cambios desde último release
- [ ] Docker images taggeadas: `audity-api:v0.x.y`, `audity-worker:v0.x.y`, `audity-frontend:v0.x.y`

### Migrations
- [ ] Backup de producción ANTES de migración
- [ ] `alembic upgrade head` ejecutado en staging → verificado
- [ ] `alembic upgrade head` ejecutado en producción
- [ ] Verificar queries post-migración: `SELECT count(*) FROM projects` por org

### Rollback Plan
- [ ] Documentar: ¿Puede `alembic downgrade -1` deshacer la migración?
- [ ] Si NO: documentar procedimiento manual de rollback
- [ ] Backup pre-release verificado y accesible
- [ ] Procedimiento para revert Docker images a version anterior

### Deploy Steps
```bash
# 1. Pre-deploy backup
scripts/backup.sh

# 2. Pull new images
docker compose pull api worker frontend

# 3. Migrate
docker compose exec -T api uv run alembic upgrade head

# 4. Rolling restart
docker compose up -d --no-deps api
docker compose up -d --no-deps worker
docker compose up -d --no-deps frontend

# 5. Health check
curl -f https://localhost:5443/api/health
curl -f https://localhost:5443/api/readyz  # cuando se implemente

# 6. Smoke test
docker compose exec -T api uv run python -m app.scripts.demo_audit
```

---

## Post-Release

### Monitoreo (primeras 24h)
- [ ] Dashboard Grafana: latencia p95 < 2s
- [ ] Rate-limit counter no muestra spikes anómalos
- [ ] Quarantine counter = 0 (o solo archivos legítimamente infectados)
- [ ] No errors en logs de API (`docker compose logs api --tail=100`)
- [ ] No errors en logs de worker (`docker compose logs worker --tail=100`)
- [ ] Temporal UI: no hay workflows stuck o failed

### Alertas Configuradas
- [ ] API error rate > 5% en 5 minutos → alerta
- [ ] p95 latency > 5s en 5 minutos → alerta
- [ ] Worker disconnected de Temporal > 2 minutos → alerta
- [ ] Disk usage > 80% en volumes → alerta
- [ ] Redis memory > 80% → alerta

### SLO Objetivos
| Métrica | Target | Medición |
|---------|--------|----------|
| API availability | 99.5% | Uptime checks cada 30s |
| Request latency p95 | < 2s | Prometheus histogram |
| Audit run completion | < 10 min p95 | Temporal workflow duration |
| Evidence upload success | > 99% | Upload success/failure counter |
| Data durability | 0 loss | Backup + restore verification semanal |

### Soporte Post-Release
- [ ] Canal de comunicación con pilotos establecido (Slack/Teams/email)
- [ ] Runbook accesible para on-call: `docs/runbook.md`
- [ ] Procedimiento de escalación documentado
- [ ] Log de incidentes iniciado
