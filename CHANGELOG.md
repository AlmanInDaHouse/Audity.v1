# Changelog

## Unreleased - Phase Closure

### Product coherence

- Se refuerza la separacion entre `control posture` de `audit_runs` y `formal risk`.
- La UI de proyecto expone el `formal risk register` con evaluaciones versionadas, treatments y resumen de trazabilidad.
- Se alinean copies activas de portfolio, runs, reports y overview para evitar ambiguedad semantica.

### Frontend public contract

- `frontend/lib/types.ts` incorpora los tipos publicos de `risk_register`, `risk_scenario_evaluation` y `risk_treatment_decision`.
- `RiskOverview` refleja el payload real entregado por backend.
- El test E2E de la pestana Risk valida que el registro formal se muestra al abrir la pestana.

### Release and docs

- `README.md` pasa a reflejar el estado real del producto y sus documentos canonicos.
- `docs/pr3b_postgres_release_check.md` se actualiza con el estado verificado en Postgres real.
- `docs/final_gap_analysis.md` deja de listar gaps historicos ya cerrados y pasa a describir deuda residual real de cierre.
