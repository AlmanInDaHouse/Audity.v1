# Audity — Risk Register

## Escala

- **Impacto**: 1 (bajo) → 5 (catastrófico)
- **Probabilidad**: 1 (raro) → 5 (casi seguro)
- **Severidad**: Impacto × Probabilidad (1-25)
- **Estado**: 🔴 Open | 🟡 Mitigating | 🟢 Mitigated | ⚪ Accepted

---

## Riesgos Técnicos

| ID | Riesgo | Impacto | Prob. | Sev. | Mitigación | Owner | Estado |
|----|--------|---------|-------|------|------------|-------|--------|
| T01 | **RLS bypass no detectado** por queries que no pasan por `set_current_org` | 5 | 2 | 10 | Tests integración RLS en CI; code review obligatorio para queries nuevas; linter custom para `select()` sin tenant filter | Backend Lead | 🟡 |
| T02 | **Secrets hardcoded** en config defaults desplegados a producción | 5 | 3 | 15 | Fail-fast en startup si `secret_encryption_key` o `vault_token` tienen valores default; CI check | Security Lead | 🔴 |
| T03 | **Ed25519 signing keys se regeneran** en restart (EnvSecretStore in-memory) | 4 | 4 | 16 | Persistir keys en Vault o DB; documentar que `env` backend es solo para dev | Backend Lead | 🔴 |
| T04 | **PDF engine genera stub** si WeasyPrint no está instalado | 3 | 3 | 9 | Dockerfile prod incluye WeasyPrint; startup assertion verifica import | DevOps | 🔴 |
| T05 | **AV scanner bloquea event loop** con socket sync | 3 | 3 | 9 | Migrar a `asyncio.open_connection` o `run_in_executor` | Backend Lead | 🔴 |
| T06 | **Feature flags en memoria** se pierden en restart/multi-replica | 3 | 4 | 12 | Persistir en DB tabla `feature_overrides` | Backend Lead | 🔴 |
| T07 | **N+1 API queries en frontend** degradan rendimiento con muchos proyectos | 2 | 4 | 8 | Consolidar con endpoint backend `/org-audit-runs` y `/org-reports` | Frontend Lead | 🟡 |
| T08 | **AI adapters son stubs** — usuario espera AI real | 3 | 3 | 9 | No publicitar AI hasta tener ≥1 adapter real; disclaimer en UI | Product | 🟡 |
| T09 | **`asyncio.create_task` fire-and-forget** en inline workflow mode | 4 | 3 | 12 | Forzar Temporal en producción; eliminar inline mode | Backend Lead | 🟡 |
| T10 | **boto3 sync calls** en async storage (S3ObjectStore) | 3 | 3 | 9 | Migrar a `aiobotocore` o `run_in_executor` | Backend Lead | 🟡 |

## Riesgos Operativos

| ID | Riesgo | Impacto | Prob. | Sev. | Mitigación | Owner | Estado |
|----|--------|---------|-------|------|------------|-------|--------|
| O01 | **Backup no probado** — restore puede fallar cuando se necesita | 5 | 2 | 10 | Nightly restore smoke en CI; verificación manual mensual | DevOps | 🟡 |
| O02 | **Sin readiness probe** — pod recibe tráfico sin estar listo | 3 | 3 | 9 | Implementar `/readyz` con checks de DB/Redis/MinIO | DevOps | 🔴 |
| O03 | **Sin alerting configurado** en producción | 4 | 3 | 12 | Configurar alertas Prometheus/Grafana para latencia, errors, disk | DevOps | 🔴 |
| O04 | **Temporal worker crash** no detectado | 4 | 2 | 8 | Health check en compose; Temporal UI monitoring; alert si worker disconnects | DevOps | 🟡 |
| O05 | **Redis sin AUTH** — manipulación de rate limits/cache | 3 | 2 | 6 | Configurar Redis AUTH en producción | DevOps | 🔴 |
| O06 | **Log rotation** no configurada — disk fill | 2 | 3 | 6 | Configurar Loki retention; Docker log driver limits | DevOps | 🟡 |

## Riesgos de Seguridad

| ID | Riesgo | Impacto | Prob. | Sev. | Mitigación | Owner | Estado |
|----|--------|---------|-------|------|------------|-------|--------|
| S01 | **Mock login como backdoor** en producción | 5 | 4 | 20 | Gate a `APP_ENV=dev`; CI test verifica que falla en `APP_ENV=production` | Security Lead | 🔴 |
| S02 | **CORS allow_methods=*** permite ataques cross-origin | 3 | 3 | 9 | Restringir a GET, POST, PUT, PATCH, DELETE; headers explícitos | Security Lead | 🔴 |
| S03 | **SSRF via integration config_json** URLs | 4 | 2 | 8 | Validar URLs de integración contra allowlist de dominios; no localhost/internal | Backend Lead | 🟡 |
| S04 | **Upload abuse** — archivos maliciosos o oversized | 3 | 3 | 9 | MIME allowlist activo; size limit por plan; ClamAV en profile `av` | Security Lead | 🟡 |
| S05 | **Header injection** via `Content-Disposition` filename | 3 | 2 | 6 | Sanitizar `evidence.name` con `urllib.parse.quote` | Backend Lead | 🔴 |
| S06 | **SCIM token timing attack** — O(n) decrypt comparison | 2 | 2 | 4 | Almacenar hash del token para lookup directo | Backend Lead | 🟡 |
| S07 | **XSS en reports HTML** — Jinja templates con user input | 4 | 2 | 8 | Autoescape activo en Jinja2 (ya configurado); CSP headers | Security Lead | 🟢 |

## Riesgos Legales

| ID | Riesgo | Impacto | Prob. | Sev. | Mitigación | Owner | Estado |
|----|--------|---------|-------|------|------------|-------|--------|
| L01 | **DPA (Data Processing Agreement)** no firmado con clientes | 4 | 4 | 16 | Template en `docs/legal-kit/`; firmar antes de onboarding | Legal/Sales | 🟡 |
| L02 | **Prometer compliance** que Audity no puede garantizar | 5 | 3 | 15 | Disclaimers explícitos en UI y documentación; "readiness" no "compliance" | Product | 🟡 |
| L03 | **Data residency** no controlada (MinIO puede estar en cualquier región) | 3 | 2 | 6 | Documentar que cliente elige región de deployment; multi-region roadmap | DevOps | ⚪ |
| L04 | **AI alucinaciones** generan reportes con información incorrecta | 4 | 3 | 12 | Confidence scores visibles; "heuristic" label; disclaimer de AI-assisted | Product/Legal | 🟡 |

## Riesgos de Producto

| ID | Riesgo | Impacto | Prob. | Sev. | Mitigación | Owner | Estado |
|----|--------|---------|-------|------|------------|-------|--------|
| P01 | **Scope creep** — añadir features sin cerrar gaps core | 3 | 4 | 12 | Release checklist obliga cerrar P0 antes de P1; backlog priorizado | Product | 🟡 |
| P02 | **Catálogos incompletos** impiden demos reales | 5 | 5 | 25 | Prioridad P0: ≥30 controles ISO, ≥20 ENS, ≥15 RGPD | Product | 🔴 |
| P03 | **Frontend no refleja capacidades backend** | 3 | 3 | 9 | Alinear UI con features enterprise activas; tests E2E | Frontend Lead | 🟡 |
| P04 | **Pricing model sin billing** real | 2 | 2 | 4 | Documentar como "self-hosted billing"; Stripe roadmap P2 | Product | ⚪ |
| P05 | **Sustitucion futura de motor de conocimiento no planificada** | 3 | 3 | 9 | Mantener `knowledge_engine` local-first desacoplado y sin LLM remoto en runtime | Product | 🟡 |

---

## Top 5 Riesgos por Severidad

1. **P02** (25) — Catálogos incompletos: el producto no puede venderse
2. **S01** (20) — Mock login en producción: backdoor abierta
3. **T03** (16) — Signing keys se regeneran: cadena de confianza rota
4. **L01** (16) — DPA no firmado: riesgo legal en piloto
5. **T02** (15) — Secrets hardcoded: breach catastrófico
