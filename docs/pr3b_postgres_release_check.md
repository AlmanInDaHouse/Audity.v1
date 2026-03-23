# PR3B Postgres Release Check

Estado actual verificado:

- `alembic current = 0010_risk_engine_treatments_traceability` en head.
- Las tablas PR3B existen en PostgreSQL real.
- RLS esta habilitado y forzado en tablas PR3B.
- Las policies `tenant_isolation_*` estan presentes.
- La API arranca contra Postgres migrado.
- Smoke funcional validado en Postgres real:
  - `GET /projects/{project_id}/risk/register`
  - `POST /projects/{project_id}/risk/scenarios/{scenario_id}/evaluations`
  - `GET /projects/{project_id}/risk/scenarios/{scenario_id}/traceability`

Conclusiones de release:

- PR3B queda cerrado a nivel de esquema, aislamiento multi-tenant y smoke API.
- El riesgo formal se mantiene separado del `control posture` de `audit_runs`.
- El motor formal en esta fase es `deterministic-v1` y su cadena de trazabilidad queda persistida.

Verificaciones recomendadas antes de un despliegue adicional:

```bash
cd backend
alembic current
alembic upgrade head
```

Checks minimos de operacion:

- Confirmar `head` en la base objetivo.
- Confirmar que las tablas `risk_scenario_evaluations` y `risk_treatment_decisions` mantienen RLS.
- Ejecutar el smoke HTTP de riesgo formal tras cada migracion productiva.
