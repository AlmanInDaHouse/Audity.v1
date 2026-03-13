# Legal Onboarding and DPA Gate

## Purpose
Bloquear el onboarding productivo de clientes o partners hasta que exista constancia verificable del DPA.

## Implemented Data Model
- `organizations.dpa_status`
- `organizations.dpa_signed_at`
- `organizations.dpa_reference`
- `organizations.onboarding_status`
- `organizations.onboarding_completed_at`

## Supported States
### DPA
- `pending`
- `requested`
- `signed`

### Onboarding
- `pending_dpa`
- `pending`
- `completed`

## Backend Flow
1. Al crear una organizacion:
   - `dpa_status=pending`
   - `onboarding_status=pending_dpa`
2. Un admin puede consultar estado:
   - `GET /organizations/{org_id}/legal/onboarding`
3. Un admin puede actualizar DPA:
   - `PUT /organizations/{org_id}/legal/dpa`
4. Completar onboarding:
   - `POST /organizations/{org_id}/legal/onboarding/complete`
   - devuelve `409` si `dpa_status != signed`

## Frontend Flow
- La pagina `enterprise` muestra estado actual, referencia de DPA y acciones:
  - `Mark DPA requested`
  - `Register signed DPA`
  - `Complete onboarding`
- El boton de completar onboarding queda deshabilitado si no hay DPA firmado.
- `overview` y `dashboard` muestran la senal legal como parte del readiness del cliente.

## Minimal Legal Kit
- Base documental ubicada en `docs/legal-kit/`.
- Esta implementacion no pretende sustituir revision legal externa.
- El objetivo es dejar un gate operativo, auditable y demostrable.
