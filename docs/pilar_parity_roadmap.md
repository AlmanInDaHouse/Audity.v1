# PILAR Parity Roadmap

## Objective
Igualar o superar la propuesta de valor de PILAR en consultoria espanola, ENS, ISO, privacidad y trazabilidad, sin prometer funcionalidades sin base tecnica.

## Workstreams
| Linea | Gap actual | Capacidad objetivo | Diseno propuesto en Audity | Dependencias | Esfuerzo | Prioridad | Riesgo | Quick win vs estructural |
|---|---|---|---|---|---|---|---|---|
| 1. Catalogos ISO / ENS / RGPD | ISO reforzado pero ENS/RGPD aun cortos | Catalogos profundos y versionados por framework | Motor de catalogos con YAML versionados, checksum, taxonomia comun y loaders validados | Equipo GRC, normalizacion de schema, QA de catalogos | M | P0 | Medio | Quick win: ampliar YAML; estructural: taxonomia comun y version governance |
| 2. Control -> evidencia -> evaluador -> hallazgo | Relacion parcial y poco navegable | Trazabilidad completa de cada control a evidencia y resultado | Grafo relacional `control_mapping` + `evidence_requirements` + `evaluation_trace` visible en UI y reportes | DB migrations, backend mappings, UI drill-down | L | P0 | Medio | Quick win: mappings YAML; estructural: vistas y auditor trail completo |
| 3. Control -> salvaguarda / tratamiento | Tratamiento de riesgo aun separado del control | Salvaguardas reutilizables y enlazadas a controles | Tabla `safeguards` + `risk_treatments` + matrices control/salvaguarda por framework | Modelo riesgo, UI remediation, report templates | L | P1 | Medio | Quick win: campos y linking; estructural: workflow de tratamiento |
| 4. Vistas de madurez / satisfaccion | Readiness simple de alto nivel | Madurez por dominio, control y organizacion | Scorecards por dominio, cobertura, evidencia minima y estado de implantacion | Catalog metadata, analytics endpoints, charts | M | P1 | Bajo | Quick win: scorecards; estructural: benchmarking historico |
| 5. Reportes potentes y personalizables | PDF ejecutivo y package, poca parametrizacion | Reportes auditables por plantilla, audiencia y framework | Plantillas Jinja versionadas, bloques configurables, filtros y anexos por control/riesgo | Reporting engine, template governance, QA legal | M | P0 | Medio | Quick win: nuevas secciones; estructural: builder de plantillas |
| 6. Privacidad / RGPD operativo | DPA gate resuelto, operativa RGPD limitada | Inventario de tratamientos, base juridica, proveedores y evidencias | Modulo ligero de privacidad con `processing_activities`, `legal_basis`, `processors`, `dpia` | Modelo RGPD, catalogo privacidad, UX admin | L | P0 | Medio | Quick win: catalogo RGPD y estados; estructural: modulo completo |
| 7. Trazabilidad de analisis y tratamiento del riesgo | Riesgo visible en audit runs, no end-to-end | Flujo completo de identificacion, evaluacion, decision y seguimiento | `risk_register`, `risk_assessments`, `treatment_decisions`, `acceptance_records` con audit log | DB, reporting, permissions, dashboard | L | P0 | Medio | Quick win: register basico; estructural: workflow completo |
| 8. Roadmap comercial para consultorias espanolas | Buen core tecnico, poco packaging sectorial | Aceleradores por ENS, ISO y privacidad para canal consultoria | Bundles de catalogos, plantillas de reporte, onboarding legal y configuracion por sector | Producto, legal kit, docs, enablement | M | P1 | Bajo | Quick win: bundles y docs; estructural: programa partner |

## Sequencing
1. P0 inmediato: profundizar catalogos ENS/RGPD, mappings control-evidencia, roadmap de reportes y registro de riesgos.
2. P1 posterior: salvaguardas/tratamientos y scorecards de madurez.
3. P2 comercial: bundles de consultoria, benchmarking y automatizacion avanzada.

## Concrete Next Deliverables
- `catalogs/ens_measures.v2.yml`
- `catalogs/rgpd_operations.v2.yml`
- esquema `control_mapping` y `risk_register`
- report templates por `executive`, `technical`, `customer-ready`
- vistas UI para trazabilidad y madurez
