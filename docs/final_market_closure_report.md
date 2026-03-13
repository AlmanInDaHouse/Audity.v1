# Audity Pre-GA Market Closure Report

## Executive Summary
Audity queda cerrado para una salida pre-GA con foco en estabilidad, seguridad y demo profesional. El runtime ya no expone el AI orchestrator remoto, el acceso de demo queda bloqueado fuera de entornos controlados, los secretos inseguros fallan en arranque, las claves de firma sobreviven reinicios y el onboarding productivo queda bloqueado sin DPA firmado.

## Scope Closed
- AI orchestrator retirado del runtime principal y de la UI. El repo conserva artefactos historicos/legacy, pero no estan expuestos por rutas activas del producto.
- `mock_login` bloqueado fuera de `dev`, `development`, `local` y `demo_controlado`.
- Secretos obligatorios y configuracion insegura con `fail-fast` en entornos productivos.
- Persistencia de claves de firma con soporte para `OIDC_PRIVATE_KEY_B64`, `OIDC_PRIVATE_KEY_PATH` y almacenamiento cifrado en DB para secretos de integracion.
- DPA operacional por organizacion con estado, referencia, fecha de firma y bloqueo de onboarding.
- Catalogo ISO 27001 ampliado a 36 controles reales.
- Connectors sin `mock_fallback`: devuelven `unconfigured` o `error` sin inventar datos.
- Frontend con auth guard real, rutas protegidas y consumo agregado de portfolio para eliminar el N+1 principal.
- PDF falso eliminado. Cuando falta runtime real, la ejecucion falla de forma explicita.

## Release Evidence
- Backend tests relevantes en verde: seguridad, persistencia de firma, dashboard, catalogo, connectors, DPA y retirada del orchestrator.
- Frontend `lint` y `build` limpios.
- Smoke HTTP reproducible del frontend:
  - `GET /projects` sin sesion responde `307 /login`
  - `GET /login` con cookie de sesion responde `307 /overview`
- Smoke funcional backend reproducible:
  - `login -> create audit_run -> poll`
  - el flujo termina en `failed` cuando falta el runtime nativo de WeasyPrint
  - la ejecucion falla de forma explicita y no entrega PDF fake

## Residual Risk
- No se pudo ejecutar la validacion Docker del PDF real en esta maquina porque el daemon Docker no estaba disponible.
- El backend local usado para smoke en Windows no puede cargar las librerias nativas de WeasyPrint; la validacion real queda pendiente de CI o de un host con Docker operativo.
- Permanecen artefactos legacy en el repo (`backend/app/ai_orchestrator`, migraciones historicas y pruebas sueltas) por compatibilidad de despliegue, pero no forman parte del runtime principal.

## Required Production Variables
- `APP_ENV`
- `DATABASE_URL`
- `SECRET_ENCRYPTION_KEY`
- `OIDC_PRIVATE_KEY_B64` o `OIDC_PRIVATE_KEY_PATH`
- `SECRET_STORE_BACKEND=db|vault`
- `VAULT_TOKEN` cuando `SECRET_STORE_BACKEND=vault`
- `CATALOG_DIR`

## Go/No-Go View
- `Go` para pre-GA controlado con despliegue en contenedor y checklist de variables obligatorias.
- `No-Go` para GA hasta automatizar validacion Docker del PDF real, cerrar pipeline release y completar roadmap de paridad catalogos/privacidad/riesgo.
