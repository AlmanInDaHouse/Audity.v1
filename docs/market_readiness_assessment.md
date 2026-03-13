# Audity — Market Readiness Assessment (Go-To-Market)

## 1. ICP — Ideal Customer Profile

### Perfil Primario: Consultorías de Cumplimiento / Certificadoras

| Atributo | Valor |
|----------|-------|
| **Tamaño** | 5-100 consultores |
| **Vertical** | GRC, compliance, ciberseguridad, auditoría |
| **Clientes finales** | PYMEs y mid-market que necesitan ISO 27001, ENS, RGPD |
| **Pain principal** | Horas manuales en recopilación de evidencia, generación de informes, seguimiento de hallazgos |
| **Comprador** | Socio/Director de servicios, Head of GRC Practice |
| **Decisor técnico** | Consultor senior / Lead auditor |
| **Presupuesto típico** | €500-5.000/mes por plataforma |
| **Ciclo de venta** | 2-6 semanas con POC |

### Perfil Secundario: MSSPs (Managed Security Service Providers)

| Atributo | Valor |
|----------|-------|
| **Tamaño** | 20-200 empleados |
| **Vertical** | Servicios de seguridad gestionada |
| **Pain principal** | Escalar auditorías compliance sin escalar equipo |
| **Diferenciador Audity** | Multi-tenancy nativo → un MSSP gestiona N clientes finales |
| **Presupuesto típico** | €1.000-10.000/mes |

### Perfil Terciario: Empresas con Auditoría Interna

| Atributo | Valor |
|----------|-------|
| **Tamaño** | 200-2.000 empleados |
| **Vertical** | Tecnología, fintech, salud |
| **Pain principal** | First-party compliance sin contratar consultora |
| **Diferenciador Audity** | 1-click audit + AI copilot reduce de semanas a horas |

---

## 2. Propuesta de Valor

### Headline
> **Audity reduce un 60% las horas de auditoría de compliance** al automatizar recopilación de evidencia, evaluación de controles y generación de paquetes de auditoría firmados — todo en una plataforma multi-tenant para consultorías.

### Puntos de valor concretos

| Pain del cliente | Cómo lo resuelve Audity | Evidencia técnica |
|------------------|--------------------------|-------------------|
| "Recopilar evidencias lleva semanas" | Connectors automáticos (GitHub, Google Workspace, Jira) + upload manual | `workflow_runtime.py` activities de evidence collection |
| "Generar informes es manual y propenso a errores" | 1-Click Audit → Informe PDF ejecutivo con risk score | `package_export.py` HTML+PDF+sign |
| "No puedo demostrar integridad de evidencias" | Firma Ed25519 + hash-chain + verification endpoint | `signing.py` + `audit_log.py` |
| "Gestionar múltiples clientes es un infierno" | Multi-tenant nativo con RLS + RBAC por organización | RLS policies + `tenancy.py` |
| "El auditor necesita un paquete listo" | Auditor Package: ZIP con evidencias + manifests + signatures | `/export/package` endpoint |
| "Remediar hallazgos se pierde en el ruido" | Remediation tasks con SLA + Jira sync bidireccional | `remediation_tasks` + Jira connector |
| "No tengo visibilidad del riesgo real" | Dashboard ejecutivo con risk score y readiness checklist | Frontend `overview/page.tsx` |

---

## 3. Packaging — Estructura de Planes

### Recomendación de Planes

| Plan | Target | Módulos Incluidos | Precio Sugerido* |
|------|--------|-------------------|------------------|
| **Starter** | Consultor individual / POC | 1 org, 3 proyectos, catálogo ISO 27001, reports PDF, 5GB evidencia | Free trial → €199/mes |
| **Professional** | Consultora pequeña (5-20) | 3 orgs, proyectos ilimitados, ISO+ENS+RGPD, Jira, 50GB, RBAC básico | €499-799/mes |
| **Enterprise** | Consultora/MSSP grande | Orgs ilimitadas, SCIM, OIDC/SSO, Vault, AV scanning, auditor packages, 500GB, ABAC, API full | €1.500+/mes (negociación) |
| **On-Premise** | Clientes con requisitos de data residency | Self-hosted, soporte premium, SLA | License fee + soporte anual |

*Precios orientativos, a validar con mercado.

### Módulos que gatan por plan

| Módulo | Starter | Professional | Enterprise |
|--------|---------|-------------|------------|
| ISO 27001 | ✅ | ✅ | ✅ |
| ENS | ❌ | ✅ | ✅ |
| RGPD | ❌ | ✅ | ✅ |
| Evidence signing | ❌ | ✅ | ✅ |
| Auditor package export | ❌ | ✅ | ✅ |
| Jira integration | ❌ | ✅ | ✅ |
| SCIM provisioning | ❌ | ❌ | ✅ |
| SSO/OIDC | ❌ | ❌ | ✅ |
| Vault secret store | ❌ | ❌ | ✅ |
| ClamAV scanning | ❌ | ❌ | ✅ |
| RBAC/ABAC | Básico | RBAC | RBAC+ABAC |
| AI evaluator | Heuristic | LLM básico | LLM + debate |
| Custom branding | ❌ | ❌ | ✅ |

---

## 4. Proceso de Onboarding para Consultorías

### Flujo de Onboarding (multi-tenant)

```
Semana 1: Setup + Configuración
├── 1. Crear organización del partner (consultora)
├── 2. Configurar OIDC/SSO (si Enterprise)
├── 3. Provisioning usuarios via SCIM (si Enterprise) o manual
├── 4. Activar catálogos requeridos (ISO/ENS/RGPD)
└── 5. Configurar integraciones (Jira, GitHub)

Semana 2: Piloto con 1-2 Clientes Reales
├── 6. Crear organizaciones de clientes finales
├── 7. Crear proyectos por cliente → asociar integraciones
├── 8. Subir evidencia manual + conectar automática
├── 9. Ejecutar 1-Click Audit → revisar findings
└── 10. Generar auditor package → revisar con equipo

Semana 3: Validación
├── 11. Feedback del equipo de auditoría
├── 12. Ajustar configuración y flujos
├── 13. Demo a partner decision maker
└── 14. Go / No-Go para rollout completo
```

### Criterios de éxito del onboarding

- [ ] ≥1 audit run completado con findings reales
- [ ] Auditor package descargado y revisado por auditor senior
- [ ] Multi-tenant verificado: partner ve solo sus clientes
- [ ] Feedback NPS ≥ 7 del equipo

---

## 5. Modelo de Partnership

### Opciones para Consultorías

| Modelo | Descripción | Revenue | Compromiso |
|--------|-------------|---------|------------|
| **SaaS Directo** | Consultora compra licencias, gestiona sus clientes | Suscripción mensual/anual | Bajo — self-service |
| **Revenue Share** | Consultora revende valor añadido a clientes finales | 70/30 o 80/20 split con consultora | Medio — co-selling |
| **White-label Lite** | Reports con marca de consultora, config de `report_brand_name` | Premium sobre plan Enterprise | Alto — partnership dedicado |
| **Implementación On-Premise** | Audity desplegado en infra del cliente | License fee + soporte anual | Alto — dedicated support |

### White-label Capacidades Actuales

- `report_brand_name` y `report_support_email` configurables por org
- Reports HTML/PDF generados con template customizable
- No hay rebranding completo de frontend (requiere fork o config adicional)

---

## 6. Objeciones Típicas y Respuestas

| Objeción | Respuesta | Evidencia |
|----------|-----------|-----------|
| "¿Cómo garantizan la seguridad de nuestros datos?" | Multi-tenancy con RLS a nivel de PostgreSQL. Cada query valida `app.current_org_id`. Role de DB sin bypass RLS. Encryption at rest + in transit. | `0004_rls_tenant_isolation.py` + `001_app_role.sql` + tests integración RLS |
| "¿Podemos hacer lock-in de datos?" | Export completo vía auditor package (ZIP con evidencias + JSON). Sin lock-in de formato. | `/export/package` endpoint |
| "¿La evidencia es íntegra?" | Firma Ed25519 + hash SHA-256 por archivo + verification endpoint | `signing.py` + `/verify-signature` |
| "¿Puedo confiar en el audit log?" | Hash-chain inmutable SHA-256. Cualquier alteración rompe la cadena. | `audit_log.py` hash chain |
| "¿Funciona con nuestro IdP?" | OIDC/SAML vía Keycloak o directo con JWKS. SCIM v2 para provisioning. | `security.py` OIDC + `enterprise.py` SCIM endpoints |
| "¿Como evaluais evidencia hoy?" | Evaluacion determinista y trazable apoyada en reglas, catalogos y `knowledge_engine` local-first. La revision humana sigue siendo obligatoria. | `knowledge_engine.py` + reportes con trazabilidad |
| "¿Y si Audity desaparece?" | Self-hosted option disponible. Evidencia siempre exportable. Código puede auditarse. | Export + on-premise model |
| "¿Cuánto tarda implementar?" | POC en 1 semana. Producción en 2-3 semanas con onboarding dedicado. | Onboarding flow documentado |

---

## 7. Demo Realista + Proof Points

### Demo Script (30 minutos)

| Min | Paso | Qué se muestra | Proof Point |
|-----|------|----------------|-------------|
| 0-3 | Login + overview | Dashboard con métricas, readiness checklist | "Vista ejecutiva inmediata" |
| 3-8 | Crear proyecto + configurar integración | Flujo tab-based, Jira connector, secret ref | "Configuración en minutos, no días" |
| 8-15 | 1-Click Audit | Workflow ejecutándose, findings apareciendo | "Auditoría automatizada completa" |
| 15-20 | Hallazgos + Remediation | Tabla findings, severity, tasks con SLA | "Del hallazgo al fix con tracking" |
| 20-25 | Evidence library + signature | Upload, scan status, verify signature | "Integridad verificable de evidencia" |
| 25-28 | Report download + auditor package | PDF descargable, ZIP con manifests | "Paquete listo para auditor externo" |
| 28-30 | Enterprise settings | Feature flags, pricing, multi-tenant | "Gestión enterprise centralizada" |

### Acceptance Report como Proof Point

- `docs/enterprise_acceptance_report.md` documenta todas las fases completadas con comandos reproducibles.
- 22 tests unitarios + 3 tests integración RLS pasando.
- Demo audit script ejecutable: `python -m app.scripts.demo_audit`.

---

## 8. Riesgos Comerciales y Mitigaciones

| Riesgo | Impacto | Probabilidad | Mitigación |
|--------|---------|--------------|------------|
| "Catálogo ISO incompleto" detectado en demo | Alto | Alta | Completar ≥30 controles ANTES de primera demo real |
| Competidor maduro (Pilar/Vanta) ya tiene tracción | Alto | Media | Posicionar en nicho hispano + multi-tenant para consultorías |
| Cliente pide SOC 2 Type II y no tenemos | Medio | Media | Compliance kit + roadmap transparente. No prometer lo que no hay. |
| AI devuelve resultado incorrecto en demo | Alto | Media | Usar controles con evidencia controlada en demo. Never live-demo con LLM sin guardrails. |
| Pricing incorrecto aleja a early adopters | Medio | Media | Empezar con free trial → pricing consultivo basado en feedback |
| Churn por falta de features vs. competidor | Alto | Media | Roadmap público con commitment dates. Early adopter pricing. |
| Data breach en piloto daña marca | Crítico | Baja | Cerrar P0 de seguridad ANTES de onboarding. Pentest básico. |

---

## 9. Conclusión GTM

### ¿Listo Para Vender como Piloto/POC a Consultorías?

**Sí — condicionado a cerrar los 7 P0s del gap analysis** (2-3 semanas de trabajo). Específicamente:

1. ✅ Multi-tenant funcional con RLS verificada
2. ✅ Workflow end-to-end: proyecto → audit → findings → remediation → report
3. ✅ Auditor package con signatures
4. ✅ Frontend feature-rich con 14 páginas
5. ⚠️ Catálogos: necesitan ≥30 controles ISO reales
6. ⚠️ Mock login: necesita gate a dev
7. ⚠️ PDF engine: necesita WeasyPrint en prod

### Plan GTM Recomendado

| Fase | Duración | Objetivo | Métrica |
|------|----------|----------|---------|
| **Pre-launch** | 2-3 semanas | Cerrar P0s + preparar demo | 7/7 P0 cerrados |
| **Alpha** | 1-2 meses | 2-3 consultorías en piloto gratuito | ≥1 audit completo por partner |
| **Beta** | 2-3 meses | 5-10 partners en beta pricing | NPS ≥ 7, retention ≥ 80% |
| **GA** | Mes 6+ | Launch público con pricing definido | MRR ≥ €5K |
