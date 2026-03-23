from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MAX_UPLOAD_MB = 20 * 1024


def _default_catalog_dir() -> str:
    candidate = Path(__file__).resolve().parents[2] / 'catalogs'
    if candidate.exists():
        return str(candidate)
    cwd_candidate = Path.cwd() / 'catalogs'
    return str(cwd_candidate)


def _default_oidc_key_path() -> str:
    return str(Path(__file__).resolve().parents[2] / '.data' / 'oidc_signing_key.pem')


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_env: str = 'dev'
    database_url: str = 'sqlite+aiosqlite:///./audity.db'
    redis_url: str = 'redis://localhost:6379/0'

    temporal_server: str = 'localhost:7233'
    temporal_namespace: str = 'default'
    temporal_task_queue: str = 'audit-run-queue'
    workflow_mode: str = 'inline'
    temporal_max_concurrent_activities: int = Field(default=50, ge=1, le=500)
    temporal_max_concurrent_workflow_tasks: int = Field(default=20, ge=1, le=200)

    minio_endpoint: str = 'localhost:9000'
    minio_access_key: str = 'minioadmin'
    minio_secret_key: str = 'minioadmin'
    minio_bucket: str = 'audity-evidence'
    minio_secure: bool = False
    storage_backend: str = 'memory'  # why this: tests/local run without external object store.

    catalog_dir: str = _default_catalog_dir()

    oidc_issuer: str = 'http://localhost:8000'
    oidc_key_id: str = 'audity-dev-key'
    oidc_private_key_b64: str = ''
    oidc_private_key_path: str = _default_oidc_key_path()

    api_base_url: str = 'http://localhost:8000'
    cors_allowed_origins: str = 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:53000,http://127.0.0.1:53000,http://localhost:5080,http://127.0.0.1:5080,https://localhost:5443,https://127.0.0.1:5443'
    rate_limit_per_minute: int = Field(default=120, ge=10, le=5000)
    sensitive_rate_limit_per_minute: int = Field(default=20, ge=1, le=2000)

    github_token: str = ''
    google_service_account_json_b64: str = ''
    ai_evaluator_enabled: bool = True
    llm_provider: str = 'openai_compatible'
    llm_model: str = ''
    llm_base_url: str = ''
    llm_api_key: str = ''
    groq_api_key: str = ''
    llm_timeout_seconds: int = Field(default=45, ge=5, le=300)
    llm_max_manual_evidence: int = Field(default=4, ge=1, le=20)

    # Enterprise feature flags
    enterprise_features_enabled: bool = False
    feature_auth_enterprise: bool = False
    feature_scim: bool = False
    feature_secret_store: bool = False
    feature_upload_av_scan: bool = False
    feature_signing: bool = False
    feature_tsa: bool = False
    feature_rbac_abac: bool = False
    feature_approvals: bool = False
    feature_reporting_package: bool = False
    feature_pricing: bool = False

    # External IdP / OIDC
    oidc_jwks_url: str = ''
    oidc_audience: str = ''
    oidc_token_endpoint: str = ''
    oidc_client_id: str = ''
    oidc_client_secret: str = ''
    mfa_required_sensitive: bool = False

    # Sessions
    access_token_ttl_minutes: int = Field(default=60, ge=5, le=1440)
    refresh_token_ttl_hours: int = Field(default=72, ge=1, le=24 * 30)

    # Secret store
    secret_store_backend: str = 'db'  # db|env|vault
    secret_encryption_key: str = ''
    vault_addr: str = 'http://vault:8200'
    vault_token: str = ''
    vault_mount_kv: str = 'secret'
    vault_mount_transit: str = 'transit'

    # Upload controls
    upload_default_max_mb: int = Field(default=DEFAULT_MAX_UPLOAD_MB, ge=1, le=DEFAULT_MAX_UPLOAD_MB)
    clamav_host: str = 'clamav'
    clamav_port: int = 3310
    clamav_timeout_seconds: int = Field(default=10, ge=1, le=120)

    # Timestamping
    tsa_provider: str = 'stub'  # stub|external
    tsa_url: str = ''

    # Telemetry
    telemetry_enabled: bool = False
    otlp_endpoint: str = 'http://otel-collector:4317'
    metrics_enabled: bool = True

    # Reporting
    report_pdf_engine: str = 'weasyprint'  # weasyprint|typst|playwright
    report_brand_name: str = 'Audity'
    report_support_email: str = 'security@audity.local'
    demo_org_id: str = ''

    auto_create_schema: bool = False

    @property
    def normalized_app_env(self) -> str:
        return self.app_env.strip().lower()

    @property
    def is_mock_login_enabled(self) -> bool:
        return self.normalized_app_env in {'dev', 'development', 'local', 'demo_controlado'}

    @property
    def is_production_like(self) -> bool:
        return not self.is_mock_login_enabled


INSECURE_VALUE_MARKERS = {
    '',
    'change-me',
    'changeme',
    'dev-only-key-change-me',
    'root',
    'minioadmin',
    'postgres',
    'audity',
}


def _contains_insecure_marker(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in INSECURE_VALUE_MARKERS:
        return True
    return any(marker in lowered for marker in ('change-me', 'changeme', 'example', 'placeholder'))


def _credentials_from_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    username = parsed.username or ''
    password = parsed.password or ''
    return username, password


def validate_runtime_security(settings: Settings) -> None:
    if not settings.is_production_like:
        return

    errors: list[str] = []

    if _contains_insecure_marker(settings.secret_encryption_key):
        errors.append('SECRET_ENCRYPTION_KEY must be set to a non-default value in production-like environments.')

    if settings.secret_store_backend == 'vault' and _contains_insecure_marker(settings.vault_token):
        errors.append('VAULT_TOKEN must be set to a non-default value when SECRET_STORE_BACKEND=vault.')

    if settings.secret_store_backend == 'env':
        errors.append('SECRET_STORE_BACKEND=env is not allowed in production-like environments; use db or vault.')

    if settings.storage_backend == 's3':
        if _contains_insecure_marker(settings.minio_access_key):
            errors.append('MINIO_ACCESS_KEY must not use a default/demo credential in production-like environments.')
        if _contains_insecure_marker(settings.minio_secret_key):
            errors.append('MINIO_SECRET_KEY must not use a default/demo credential in production-like environments.')

    db_user, db_password = _credentials_from_url(settings.database_url)
    if db_user and _contains_insecure_marker(db_user):
        errors.append('DATABASE_URL must not use a default database username in production-like environments.')
    if db_password and _contains_insecure_marker(db_password):
        errors.append('DATABASE_URL must not use a default database password in production-like environments.')

    redis_user, redis_password = _credentials_from_url(settings.redis_url)
    if redis_password and _contains_insecure_marker(redis_password):
        errors.append('REDIS_URL must not use a default Redis password in production-like environments.')
    if not redis_password and settings.redis_url.startswith('redis://'):
        errors.append('REDIS_URL must include authenticated access in production-like environments.')
    if redis_user and _contains_insecure_marker(redis_user):
        errors.append('REDIS_URL must not use a default Redis username in production-like environments.')

    if not settings.oidc_private_key_b64.strip() and not Path(settings.oidc_private_key_path).expanduser().exists():
        errors.append('OIDC_PRIVATE_KEY_B64 or an existing OIDC_PRIVATE_KEY_PATH file is required in production-like environments.')

    if errors:
        raise RuntimeError('Unsafe runtime configuration:\n- ' + '\n- '.join(errors))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
