# Adok Certification — Documentación Técnica

## Suposiciones técnicas razonables

- Suposición técnica razonable: la base tecnológica existente en este repositorio constituye el núcleo de la plataforma de Adok Certification, aunque algunos identificadores internos del código y la infraestructura todavía utilicen la denominación `Audity`.
- Suposición técnica razonable: Adok Certification opera como plataforma SaaS B2B orientada a certificación, auditoría, compliance, gestión de evidencia y seguimiento de remediación para clientes empresariales, consultoras y auditores externos.
- Suposición técnica razonable: la plataforma da soporte al ciclo técnico y documental de evaluación y verificación, pero no sustituye por sí sola la decisión formal de certificación ni una validación jurídica o regulatoria final por parte de una entidad acreditada.
- Suposición técnica razonable: el producto se despliega en modalidad multi-tenant por organización, con aislamiento lógico reforzado a nivel de aplicación y base de datos.

## 1. Resumen ejecutivo técnico

Adok Certification es una plataforma tecnológica para la gestión integral de procesos de certificación, auditoría y compliance. Su propósito es centralizar expedientes, documentación, evidencias, validaciones, hallazgos, remediaciones e informes en un entorno único, trazable y apto para operación empresarial.

El problema que resuelve es recurrente en procesos de auditoría y verificación: información distribuida entre correo, carpetas compartidas, hojas de cálculo, herramientas de tickets y documentos no versionados; ausencia de trazabilidad fuerte; dificultad para demostrar integridad documental; y falta de un modelo homogéneo para coordinar clientes, auditores, consultoras y validadores.

El valor tecnológico principal de Adok Certification reside en cinco capacidades:

| Capacidad | Valor aportado |
|---|---|
| Multi-tenancy empresarial | Permite operar múltiples clientes u organizaciones con aislamiento lógico y de datos. |
| Evidencia con integridad verificable | Registra hash, metadatos, firma y trazabilidad de evidencias e informes. |
| Orquestación de procesos | Estructura auditorías y evaluaciones como workflows repetibles, auditables y escalables. |
| Control de acceso granular | Combina autenticación, RBAC, ABAC y segregación por organización. |
| Reporting y paquetes de auditoría | Genera informes y artefactos exportables para revisión interna, auditoría externa o intercambio con terceros. |

La plataforma puede atender, con distintos perfiles de operación, a:

- empresas que preparan o mantienen certificaciones y programas de compliance;
- consultoras que coordinan evidencias y seguimiento de hallazgos;
- auditores internos o externos que necesitan trazabilidad y reporting consistente;
- partners tecnológicos o integradores que conectan la plataforma con sistemas corporativos;
- entidades de certificación o verificadores que requieren un expediente estructurado y verificable.

## 2. Descripción general de la plataforma

### 2.1 Visión funcional

Adok Certification funciona como una plataforma de gestión de expedientes de evaluación y certificación. Cada organización cliente dispone de su propio espacio operativo, desde el que se gestionan proyectos, auditorías, catálogos de controles, repositorios documentales, evidencias, findings, remediaciones y salidas de reporting.

La plataforma articula el ciclo completo desde el alta de cliente hasta el cierre y seguimiento del expediente. El modelo no se limita a almacenar documentos: estructura decisiones, estados, responsables, hitos y evidencias de soporte para que el resultado pueda defenderse ante dirección, auditoría o terceros.

### 2.2 Módulos principales

| Módulo | Función principal | Estado |
|---|---|---|
| Gestión de organizaciones | Alta de tenant, onboarding, política de seguridad, plan y estado legal | Actual |
| Gestión de proyectos | Agrupa el alcance operativo de auditorías o certificaciones | Actual |
| Catálogos de controles | Soporta marcos versionados de evaluación | Actual |
| Ejecución de auditorías | Lanza workflows, recopila evidencia y calcula riesgo | Actual |
| Biblioteca de evidencias | Repositorio filtrable con descarga y verificación | Actual |
| Hallazgos y remediación | Registra findings, tareas, comentarios, aprobaciones y waivers | Actual |
| Reporting | Genera informe PDF/HTML y paquete exportable de auditoría | Actual |
| Integraciones | Captura evidencia y sincroniza eventos con sistemas externos | Parcial |
| Identidad enterprise | OIDC, SCIM y políticas de MFA | Actual / configurable |
| Observabilidad y operación | Métricas, trazas y perfiles de despliegue enterprise | Actual |

### 2.3 Casos de uso principales

- Preparación de un expediente de certificación basado en controles y evidencias documentales.
- Ejecución de auditorías internas periódicas por proyecto, unidad o cliente.
- Seguimiento de remediaciones derivadas de hallazgos y su trazabilidad hasta cierre.
- Consolidación de evidencias y emisión de informes ejecutivos o paquetes para auditor externo.
- Gestión de identidades, permisos y segregación de acceso por organización y rol.
- Integración con repositorios de código, directorios corporativos y sistemas de ticketing.

### 2.4 Tipo de operaciones soportadas

- operaciones CRUD de organizaciones, proyectos, catálogos e integraciones;
- carga, almacenamiento y descarga controlada de evidencias;
- ejecución asíncrona de workflows de evaluación;
- generación de findings, tareas de remediación y comentarios;
- emisión de informes y paquetes exportables;
- verificación de firma de evidencias;
- provisión de usuarios y grupos vía SCIM;
- administración de planes, políticas de seguridad y feature flags enterprise.

## 3. Arquitectura del sistema

### 3.1 Arquitectura lógica

La arquitectura de Adok Certification responde a un patrón SaaS moderno de servicios desacoplados, con separación entre plano de presentación, plano transaccional, motor de procesos, persistencia estructurada, almacenamiento documental e integración externa.

```text
Usuarios / Partners / Auditores
            |
     Web UI / API Clients
            |
  Reverse Proxy / Ingress TLS
            |
  Frontend Next.js + Backend FastAPI
            |
   +--------+---------+---------+---------+
   |                  |         |         |
PostgreSQL         Redis      MinIO    Temporal
   |                  |         |         |
   +------ Seguridad, sesiones, evidencia, workflows ------+
            |
       Worker de procesos
            |
 Integraciones externas / reporting / conectores
```

### 3.2 Separación por capas

| Capa | Responsabilidad | Tecnología base actual |
|---|---|---|
| Presentación | Interfaz de usuario y navegación funcional | Next.js |
| API de negocio | Endpoints REST, validación, permisos, tenancy | FastAPI |
| Servicios de dominio | Auditorías, reporting, firma, secretos, reglas | Python |
| Persistencia relacional | Entidades transaccionales y trazabilidad | PostgreSQL |
| Almacenamiento de objetos | Evidencia, informes y paquetes | MinIO / S3 |
| Orquestación | Flujos asíncronos de evaluación | Temporal |
| Caché y rate limiting | Control operativo y sesión auxiliar | Redis |
| Observabilidad | Métricas y trazas | Prometheus, OTel, Grafana, Loki |

### 3.3 Frontend

El frontend ofrece un espacio de operación para equipos internos y clientes empresariales. Las vistas actuales cubren overview ejecutivo, portfolio de informes, proyectos, evidencias, integraciones y ajustes enterprise. La interfaz está orientada a seguimiento operativo y no solo a consulta documental.

### 3.4 Backend

El backend expone una API REST para autenticación, administración, auditorías, evidencias, reportes, SCIM, políticas, pricing e integraciones. Implementa dependencias de seguridad, contexto de tenant, validaciones de negocio y escritura de trazabilidad.

### 3.5 Base de datos

PostgreSQL actúa como sistema transaccional principal. El modelo de datos está organizado por `Organization` como raíz de tenant y emplea Row Level Security en tablas sensibles para reforzar el aislamiento intercliente.

### 3.6 Almacenamiento documental

Las evidencias, informes y paquetes exportables se almacenan como objetos en almacenamiento S3-compatible. La base de datos conserva las referencias, hashes, estado de escaneo, metadatos, manifiestos y firmas.

### 3.7 Colas y workflows

La ejecución de auditorías se resuelve mediante Temporal y un worker Python. Este diseño desacopla la API del procesamiento intensivo, mejora la resiliencia operativa y permite reintentos controlados, escalado independiente y trazabilidad de estados.

### 3.8 Integraciones

La arquitectura prevé dos tipos de integración:

- conectores de entrada para capturar evidencia o inventario desde sistemas corporativos;
- conectores de salida para sincronizar findings, tickets o eventos con terceros.

### 3.9 Propuesta de despliegue

La plataforma está preparada para dos modos de despliegue:

| Modo | Uso recomendado |
|---|---|
| `docker-compose` | desarrollo, demo controlada, laboratorio funcional |
| Kubernetes + Helm | staging, preproducción y producción enterprise |

En producción, la topología objetivo es:

- frontend, API y worker en despliegues independientes;
- PostgreSQL y almacenamiento de objetos gestionados o con controles equivalentes;
- ingress TLS, políticas de red y secretos externos;
- autoescalado horizontal para API, frontend y worker;
- observabilidad desacoplada del runtime de negocio.

### 3.10 SaaS multi-tenant

El modelo SaaS multi-tenant es nativo al diseño:

- el tenant raíz es la organización;
- cada petición autenticada fija un contexto de organización;
- las consultas se filtran por organización en aplicación;
- PostgreSQL refuerza el aislamiento con RLS;
- los objetos de evidencia se segmentan por ruta lógica de tenant y proyecto;
- los secretos se referencian por `secret://{org}/{name}`.

Este enfoque es adecuado para SaaS B2B con segregación fuerte sin necesidad inmediata de una base de datos por cliente. Para clientes con requerimientos elevados de residencia, soberanía o aislamiento contractual, puede evolucionar a un esquema híbrido con tenants dedicados.
