# Audity — Final Gap Analysis

## Resumen Ejecutivo

Audity ha recorrido un 75-80% del camino hacia un producto enterprise-ready. La base técnica es sólida: multi-tenancy con RLS verificada por tests de integración, RBAC/ABAC funcional, hash-chain en audit log, Ed25519 signing, workflows Temporal con retry policies, Jira connector bidireccional, observabilidad scaffolded, y un frontend funcional con 14 páginas y flujos end-to-end.

El último tramo exige foco en **tres ejes**: (1) completar el catálogo de controles para que las auditorías ISO/ENS/RGPD tengan masa crítica vendible, (2) cerrar los gaps de frontend que impiden una demo profesional (N+1 queries, falta de auth guard, inconsistencias UX), y (3) hardening de seguridad puntual (mock login gating, connector fallback, PDF engine). El runtime pre-GA ya no expone el orquestador remoto y queda preparado para una sustitución futura por un motor local-first.

**Posición vs. competidor (Pilar)**: Audity compite en catálogos ISO/ENS/RGPD + multi-tenant para consultorías (que Pilar no tiene como servicio multi-tenant). El AI evaluator y el auditor package firmado son diferenciadores claros. Lo que Pilar tiene y Audity no: catálogos completos, UI pulida, track record de implementaciones.

---

## Último Tramo: Lista Priorizada

### P0 — Bloqueantes para Piloto Comercial (2-3 semanas)

| # | Gap | Esfuerzo | Valor Comercial | Criterio de Aceptación |
|---|-----|----------|-----------------|------------------------|
| 1 | **Gate mock_login en producción** | S | Alto — elimina backdoor | `APP_ENV != dev` → endpoint devuelve 403. Test unitario lo verifica. |
| 2 | **Completar catálogo ISO 27001 a ≥30 controles** | M | Crítico — sin esto no es vendible | YAML con ≥30 controles con descriptions reales (no placeholder). Evaluator keys asignados. |
| 3 | **Fix PDF engine en Dockerfile prod** | S | Alto — PDFs reales en demos | WeasyPrint instalado en imagen Docker API. Test que genera PDF > 1KB. |
| 4 | **Fix connectors mock_fallback** | S | Alto — elimina datos inventados | GitHub/Google devuelven `mode: unconfigured` con zeros cuando no hay credenciales. |
| 5 | **Eliminar defaults hardcoded de secrets** | S | Crítico — due diligence | `secret_encryption_key` y `vault_token` sin default. App fail-fast al iniciar si no están definidos en producción. |
| 6 | **Frontend: auth guard middleware** | S | Alto — UX profesional | Middleware Next.js que redirige a `/login` si no hay sesión en páginas protegidas. |
| 7 | **Frontend: fix N+1 API queries** | M | Medio — rendimiento en demos | `audit-runs`, `reports`, `projects` hacen fetch por proyecto. Consolidar con endpoint backend dedicado. |

### P1 — Hardening para Ventas Enterprise (4-6 semanas)

| # | Gap | Esfuerzo | Valor Comercial | Criterio de Aceptación |
|---|-----|----------|-----------------|------------------------|
| 8 | Completar catálogos ENS (≥20 medidas) y RGPD (≥15 artículos) | M | Alto | YAMLs con medidas/artículos reales, evaluator keys asignados. |
| 9 | Preparar sustitucion local-first del motor de conocimiento | M | Alto | Interfaz desacoplada y sin dependencia de LLM remoto en runtime. |
| 10 | Persistir feature flags en DB (no en dict en memoria) | M | Medio | Tabla `feature_overrides` con persistencia. Flags sobreviven restart. |
| 11 | AV scanner async (eliminar blocking socket) | S | Medio | Usar `asyncio.open_connection` o threadpool. |
| 12 | Storage: forzar s3 en producción, fail-fast si es memory | S | Alto | Startup assertion si `APP_ENV=production` y `storage_backend=memory`. |
| 13 | Frontend: consistencia idiomática (todo español o todo inglés) | M | Medio | Decidir idioma y aplicar. |
| 14 | Readiness probe `/readyz` con checks de DB/Redis/MinIO | S | Medio | Endpoint devuelve 503 si alguna dependencia está caída. |
| 15 | Signing keys persistentes en Vault/DB | M | Alto | Keys no se regeneran en restart con storage persistente. |

### P2 — Escala Enterprise (6-10 semanas)

| # | Gap | Esfuerzo | Valor Comercial | Criterio de Aceptación |
|---|-----|----------|-----------------|------------------------|
| 16 | ServiceNow connector real | L | Medio | API client funcional con create/update de incidents. |
| 17 | TSA real (RFC 3161) para firmas con timestamp verificable | M | Medio | Integración con servidor TSA; token es un timestamp token RFC 3161. |
| 18 | E2E tests Playwright ejecutables | L | Medio | ≥5 flows cubiertos: login → project → audit run → findings → report download. |
| 19 | Completar validacion Docker del runtime PDF en CI | S | Alto | Build de imagen + test PDF real en pipeline de release. |
| 20 | Billing/Stripe integration | L | Alto | Webhook Stripe → actualiza pricing plan automáticamente. |
| 21 | Refactor main.py en sub-routers | M | Bajo | <300 líneas por router, cada dominio en su archivo. |

---

## Criterios para Declarar "Market-Ready"

| Criterio | Métrica de Aceptación | Estado |
|----------|-----------------------|--------|
| Catálogo ISO 27001 con ≥30 controles reales | `wc -l catalogs/iso27001_annex_a.v1.yml` ≥ 300 | ❌ (2 controles, ~25 líneas) |
| Mock login desactivado en producción | `grep -c 'mock' app/main.py` solo en dev guard | ❌ |
| PDF reports generan documentos válidos | `file report.pdf` → `PDF document` | ❌ (stub bytes) |
| RLS enforcement tests pasan en CI sobre Postgres | CI job `backend-e2e` green con RLS tests | ✅ |
| Feature flags persistentes | Restart API → flags preservados | ❌ (en memoria) |
| ≥20 tests unitarios + ≥3 integración pasando | `pytest` ≥ 23 passed | ✅ (22 passed, 1 skipped) |
| Frontend auth guard en todas las rutas protegidas | Acceso a `/overview` sin sesión → redirect a `/login` | ❌ |
| Connectors no devuelven datos inventados | `grep -c 'mock_fallback'` → 0 líneas no gateadas | ❌ |
| AI adapters ≥1 real (no stub) | Adapter con API call real | ❌ |
| Documentación técnica completa | `docs/technical_documentation.md` con ≥15 secciones | En progreso |

---

## Comparativa de Capacidades: Audity vs. Competidor GRC

| Capacidad | Audity | Competidor típico (Pilar / Vanta / Drata) |
|-----------|--------|-------------------------------------------|
| **Multi-tenant nativo (RLS)** | ✅ Postgres RLS por tabla | ⚠️ Varía (generalmente app-level) |
| **ISO 27001 Annex A** | ⚠️ 2 controles (en desarrollo) | ✅ Catálogo completo (~93+) |
| **ENS** | ⚠️ ~3-5 medidas | ✅/⚠️ (solo proveedores españoles) |
| **RGPD** | ⚠️ ~4-5 artículos | ✅ Checklist completo |
| **Evidence signing (Ed25519)** | ✅ Sign + verify + bundle | ⚠️ Pocos ofrecen crypto signing |
| **Audit log hash-chain** | ✅ SHA-256 chain tamper-evident | ⚠️ Generalmente simple append log |
| **Auditor package (ZIP)** | ✅ Con signatures + manifests | ⚠️ Export básico en algunos |
| **AI/GRC evaluation** | ⚠️ LLM con fallback heurístico | ✅/⚠️ AI en desarrollo por varios |
| **AI multi-agent orchestrator** | ⚠️ Arquitectura → stubs | ❌ Nadie tiene esto aún |
| **Jira bidirectional** | ✅ Create + webhook + status sync | ✅ Estándar en tier-1 |
| **ServiceNow** | ❌ Stub | ✅ Estándar en enterprise |
| **SCIM v2** | ✅ Users/Groups | ✅ Estándar en enterprise |
| **SSO/OIDC real** | ⚠️ Scaffolded (Keycloak profile) | ✅ Funcional de fábrica |
| **PDF reports** | ⚠️ Stub PDF sin WeasyPrint | ✅ Reports nativos |
| **Observability stack** | ✅ OTel + Prometheus + Grafana | ⚠️ Varía ampliamente |
| **Backup/restore scripts** | ✅ DB + MinIO | ✅ Estándar |
| **CI/CD pipeline** | ✅ GitHub Actions con lint+test | ✅ Estándar |
| **Temporal workflows** | ✅ Con retry + concurrency | ❌ La mayoría usa colas simples |
| **Pricing/billing gates** | ⚠️ Model sin billing real | ✅ Stripe/billing integrado |
| **Frontend UX** | ⚠️ Funcional pero con issues | ✅ Pulido |

---

## Qué NO Hacemos (Límites Explícitos)

> Declarar estos límites explícitamente protege credibilidad comercial y evita promesas peligrosas.

| Lo que NO hacemos | Por qué | Alternativa que sí ofrecemos |
|-------------------|---------|------------------------------|
| **No certificamos ISO/GDPR/ENS** | Audity es herramienta, no certificadora | "Readiness workspace" con evidencia verificable para auditores externos |
| **No hacemos penetration testing** | Fuera de scope del producto | Runbook de pentest para que el cliente contrate su proveedor |
| **No procesamos datos PCI-DSS** | Stack no está certificado PCI | Encryption at rest + in transit para datos de auditoría |
| **No garantizamos compliance automático** | AI heuristic no sustituye auditor humano | "Copiloto de auditoría" que reduce horas, no las elimina |
| **No ofrecemos SLA 99.99% hoy** | Infraestructura single-region en MVP | Arquitectura preparada para HA (Temporal + Postgres replicas) |
| **No tenemos SOC 2 Type II** | Requiere operación en producción | Compliance kit con templates para iniciar proceso |
| **No hacemos white-label completo** | Frontend requiere rebranding manual | Config de `report_brand_name` + `report_support_email` |
| **AI no sustituye GRC senior** | LLM puede alucinar | Confidence scores + source attribution + "heuristic" label visible |
