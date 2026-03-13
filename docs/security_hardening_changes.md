# Security Hardening Changes

## Closed Findings
### S01. Mock login in production
- `/auth/mock/login` devuelve `403` fuera de `dev`, `development`, `local` y `demo_controlado`.
- `GET /auth/config` expone si el entorno permite acceso demo.
- Tests cubren modo habilitado y deshabilitado.

### T02. Hardcoded secrets
- Eliminados defaults inseguros de:
  - `SECRET_ENCRYPTION_KEY`
  - `VAULT_TOKEN`
- `validate_runtime_security()` detiene el arranque si en entorno productivo faltan secretos o siguen valores inseguros.
- Tambien bloquea:
  - `SECRET_STORE_BACKEND=env` en produccion
  - credenciales por defecto de MinIO
  - `DATABASE_URL` con credenciales por defecto
  - `REDIS_URL` inseguro

### T03. Regeneracion de signing keys
- `OIDCSigner` carga clave desde:
  - `OIDC_PRIVATE_KEY_B64`
  - `OIDC_PRIVATE_KEY_PATH`
- En dev se genera una vez y se persiste en fichero.
- En produccion falla si no existe material criptografico persistente.
- Tests verifican persistencia de firma entre reinicios simulados.

### Secret persistence
- Nuevo `DatabaseSecretStore` con cifrado de sobre (`EnvelopeCipher`).
- Nueva tabla `secret_records` con unicidad por `org_id + name`.
- Preparado para `vault` cuando exista despliegue enterprise.

### Connector honesty
- Connectors sin credenciales devuelven `mode: unconfigured` y contadores a cero.
- Errores reales devuelven `mode: error`.
- Eliminado `mock_fallback` silencioso.

## Runtime Implications
- El producto ya no depende de secretos hardcodeados para arrancar.
- La demo productiva no puede cerrarse sin DPA firmado.
- El PDF ya no puede falsificarse con bytes dummy cuando falta el runtime real.

## Required Operational Controls
- Gestionar `SECRET_ENCRYPTION_KEY` con vault o secreto de plataforma.
- Proveer material de firma persistente antes de arrancar produccion.
- Ejecutar despliegues con `APP_ENV=production` o equivalente para activar `fail-fast`.
