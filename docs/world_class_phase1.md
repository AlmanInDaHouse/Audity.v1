# Audity World-Class Phase 1

## 1. Plan de Arquitectura High-Level

Audity pasa a una topologia de produccion con tres workloads stateless en Kubernetes: `api`, `worker` y `frontend`, desplegados via Helm, con `Ingress`, `HPA`, `PDB` y `Job` de migraciones. Los servicios stateful se sacan del `docker-compose` gigante y pasan a gestionarse como dependencias de plataforma: PostgreSQL HA o servicio gestionado, Redis HA, object storage S3/MinIO, Temporal y Keycloak.

Sobre esa base, Temporal orquesta los nuevos bloques funcionales:

- Ingesta y evaluacion GRC con LLM sobre evidencias limpias almacenadas en MinIO/S3.
- Generacion de executive reports PDF firmados con pipeline corporativo.
- Sincronizacion outbound con Jira y realimentacion inbound por webhook.

En frontend, Playwright cubre el critical path actual del producto: `mock SSO login -> contexto de organizacion -> 1-click audit`.

## 2. Estructura de Ficheros (Tree)

```text
backend/
  alembic/versions/0003_world_class_foundation.py
  app/
    connectors/
      __init__.py
      jira.py
    knowledge_engine.py
    package_export.py
    templates/
      executive_report.html.j2
    temporal_workflow.py
    workflow_runtime.py
  tests/
    test_world_class_foundation.py
docs/
  world_class_phase1.md
frontend/
  playwright.config.ts
  tests/e2e/critical-path.spec.ts
infra/
  helm/audity/
    Chart.yaml
    values.yaml
    templates/
      _helpers.tpl
      api-deployment.yaml
      api-hpa.yaml
      api-service.yaml
      configmap.yaml
      frontend-deployment.yaml
      frontend-hpa.yaml
      frontend-service.yaml
      ingress.yaml
      migration-job.yaml
      networkpolicy.yaml
      pdb.yaml
      secret.yaml
      worker-deployment.yaml
      worker-hpa.yaml
  k8s/bootstrap/
    namespace.yaml
    cluster-issuer.yaml
```

## 3. Implementacion Tecnica por Epica

### Epica 1. Despliegue Empresarial en Kubernetes

- Helm chart base en `infra/helm/audity` para `api`, `worker` y `frontend`.
- `Job` Helm para `alembic upgrade head` antes de instalar/actualizar.
- `Ingress` con split `/api` y `/`.
- `HPA` por CPU y memoria.
- `PDB` para evitar caidas durante mantenimiento.
- `NetworkPolicy` base para empezar a cerrar trafico entre namespaces.

Recomendacion de migracion desde `docker-compose.yml`:

1. Externalizar PostgreSQL, Redis, MinIO/S3, Temporal y Keycloak.
2. Publicar imagenes OCI de `backend`, `worker` y `frontend`.
3. Desplegar el namespace y certificados.
4. Ejecutar Helm con `values-production.yaml`.
5. Mover trafico gradualmente detras de `Ingress`.

### Epica 2. Motor local de evaluacion de evidencia

- `backend/app/knowledge_engine.py` implementa un evaluador estructurado local-first.
- El flujo:
  1. Temporal recoge evidencias manuales limpias con `object_key`.
  2. El evaluador extrae texto de `txt/json/pdf`.
  3. Si hay runtime LangChain disponible, usa `ChatOpenAI` sobre endpoint OpenAI-compatible.
  4. Si no hay LLM o falla el parseo, cae a heuristica determinista.
  5. Los veredictos se integran en `rules.evaluate_controls()` como resultados estructurados.

Salida estructurada:

- `Cumple -> pass`
- `No Cumple -> fail`
- `Recomendacion -> partial`

### Epica 3. Motor Avanzado de Reportes Ejecutivos

- `package_export.py` ahora genera un `ExecutiveReportArtifact`.
- Libreria propuesta para el motor principal: `WeasyPrint`.
  - Ventaja: HTML/CSS corporativo, pipeline Python puro y despliegue estable en workers.
  - Tipos alternativos soportados como interfaz: `typst` o `playwright` mediante `REPORT_PDF_ENGINE`.
- El Activity `generate_report_activity()` usa ya este motor para producir el PDF oficial del run y adjuntarlo como evidencia.
- El ZIP de auditoria incluye tambien `executive-report.html` y `executive-report.pdf`.

### Epica 4. Testing End-to-End Frontend

- Setup inicial con Playwright en `frontend/playwright.config.ts`.
- Test en `frontend/tests/e2e/critical-path.spec.ts`.
- Se han anadido `data-testid` a login y CTA principal.
- El boton de negocio pasa a exponerse como `Run 1-Click Audit`.

Nota: en esta iteracion el acceso de demo controlado sigue existiendo solo para entornos de desarrollo. En salida al mercado el acceso debe entrar por SSO/enterprise auth y la seleccion de organizacion debe desacoplarse en una pantalla propia.

### Epica 5. Conectores Bidireccionales Jira / ServiceNow

- `backend/app/connectors/jira.py` implementa:
  - creacion de issues en Jira cuando Temporal persiste findings,
  - tabla `external_tickets` para trazabilidad de sincronizacion,
  - webhook entrante para realimentar el finding.
- Nuevo estado: `pending_validation`.
- Cuando Jira devuelve `Closed/Done/Resolved`, Audity actualiza:
  - `Finding.status = pending_validation`
  - `RemediationTask.status = pending_validation`

El patron queda preparado para replicar ServiceNow con un conector gemelo:

- `OutboundIntegration.kind = servicenow`
- cliente proveedor
- tabla `external_tickets`
- webhook inbound con traduccion de estados

## 4. Instrucciones de Despliegue

### Local

```bash
docker compose up -d --build
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run python -m app.scripts.seed_data
```

### Helm / Kubernetes

```bash
kubectl apply -f infra/k8s/bootstrap/namespace.yaml
kubectl apply -f infra/k8s/bootstrap/cluster-issuer.yaml

helm upgrade --install audity infra/helm/audity \
  --namespace audity \
  --create-namespace \
  --values infra/helm/audity/values.yaml
```

### Backend tests focalizados

```bash
cd backend
uv run pytest -q tests/test_world_class_foundation.py tests/test_reporting.py
```

### E2E frontend

```bash
cd frontend
npm install
$env:E2E_BASE_URL="http://127.0.0.1:3000"
$env:E2E_ORG_ID="<org-id-seed>"
npm run e2e
```
