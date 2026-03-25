from __future__ import annotations

import base64

from app import main as main_module
from app.config import Settings, get_settings, validate_runtime_security
from app.rate_limit import rate_limiter
from app.security import get_signer


def _login(client, email: str, org_id: str) -> str:
    res = client.post('/auth/mock/login', json={'email': email, 'org_id': org_id})
    assert res.status_code == 200, res.text
    return res.json()['access_token']


def _reset_rate_limit_state() -> None:
    rate_limiter._memory.clear()
    rate_limiter._memory_expiry.clear()


def test_upload_rejects_disallowed_mime(client, seeded_ids):
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'])
    response = client.post(
        f"/projects/{seeded_ids['project_id']}/evidence/upload",
        data={'item_type': 'manual_upload', 'metadata_json': '{}'},
        files={'file': ('bad.exe', b'MZ-binary', 'application/x-msdownload')},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == 415


def test_upload_rejects_file_too_large(client, seeded_ids):
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'])
    too_large = b'a' * (20 * 1024 * 1024 + 1)
    response = client.post(
        f"/projects/{seeded_ids['project_id']}/evidence/upload",
        data={'item_type': 'manual_upload', 'metadata_json': '{}'},
        files={'file': ('large.txt', too_large, 'text/plain')},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == 413


def test_sensitive_rate_limit_applies_to_audit_runs(client, seeded_ids, monkeypatch):
    async def _noop_launch(_payload) -> None:
        return None

    monkeypatch.setattr(main_module, 'launch_audit_workflow', _noop_launch)
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'])
    headers = {'Authorization': f'Bearer {token}'}

    previous_limit = rate_limiter.settings.sensitive_rate_limit_per_minute
    rate_limiter.settings.sensitive_rate_limit_per_minute = 1
    _reset_rate_limit_state()
    try:
        first = client.post(
            f"/projects/{seeded_ids['project_id']}/audit-runs",
            json={'catalog_version': 'v1'},
            headers=headers,
        )
        second = client.post(
            f"/projects/{seeded_ids['project_id']}/audit-runs",
            json={'catalog_version': 'v1'},
            headers=headers,
        )
    finally:
        rate_limiter.settings.sensitive_rate_limit_per_minute = previous_limit
        _reset_rate_limit_state()

    assert first.status_code == 200
    assert second.status_code == 429


def test_global_rate_limit_returns_429_for_login(client, seeded_ids):
    previous_limit = rate_limiter.settings.rate_limit_per_minute
    rate_limiter.settings.rate_limit_per_minute = 1
    _reset_rate_limit_state()
    try:
        first = client.post(
            '/auth/mock/login',
            json={'email': seeded_ids['users']['auditor'], 'org_id': seeded_ids['org_id']},
        )
        second = client.post(
            '/auth/mock/login',
            json={'email': seeded_ids['users']['auditor'], 'org_id': seeded_ids['org_id']},
        )
    finally:
        rate_limiter.settings.rate_limit_per_minute = previous_limit
        _reset_rate_limit_state()

    assert first.status_code == 200
    assert second.status_code == 429


def test_sensitive_rate_limit_applies_to_evidence_upload(client, seeded_ids):
    token = _login(client, seeded_ids['users']['auditor'], seeded_ids['org_id'])
    headers = {'Authorization': f'Bearer {token}'}

    previous_limit = rate_limiter.settings.sensitive_rate_limit_per_minute
    rate_limiter.settings.sensitive_rate_limit_per_minute = 1
    _reset_rate_limit_state()
    try:
        first = client.post(
            f"/projects/{seeded_ids['project_id']}/evidence/upload",
            data={'item_type': 'manual_upload', 'metadata_json': '{}'},
            files={'file': ('ok.txt', b'first', 'text/plain')},
            headers=headers,
        )
        second = client.post(
            f"/projects/{seeded_ids['project_id']}/evidence/upload",
            data={'item_type': 'manual_upload', 'metadata_json': '{}'},
            files={'file': ('ok2.txt', b'second', 'text/plain')},
            headers=headers,
        )
    finally:
        rate_limiter.settings.sensitive_rate_limit_per_minute = previous_limit
        _reset_rate_limit_state()

    assert first.status_code == 200
    assert second.status_code == 429


def test_mock_login_disabled_outside_allowed_env(client, seeded_ids, monkeypatch):
    monkeypatch.setattr(main_module.settings, 'app_env', 'production')

    response = client.post(
        '/auth/mock/login',
        json={'email': seeded_ids['users']['auditor'], 'org_id': seeded_ids['org_id']},
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Mock login is disabled in this environment'


def test_mock_login_enabled_in_dev(client, seeded_ids, monkeypatch):
    monkeypatch.setattr(main_module.settings, 'app_env', 'dev')

    response = client.post(
        '/auth/mock/login',
        json={'email': seeded_ids['users']['auditor'], 'org_id': seeded_ids['org_id']},
    )

    assert response.status_code == 200
    assert response.json()['access_token']


def test_runtime_security_validation_fails_for_insecure_production_defaults():
    settings = Settings.model_construct(
        app_env='production',
        database_url='postgresql+asyncpg://postgres:postgres@db:5432/audity',
        redis_url='redis://redis:6379/0',
        minio_access_key='minioadmin',
        minio_secret_key='minioadmin',
        storage_backend='s3',
        secret_store_backend='env',
        secret_encryption_key='dev-only-key-change-me',
        vault_token='root',
        oidc_private_key_b64='',
        oidc_private_key_path='/nonexistent/key.pem',
    )

    try:
        validate_runtime_security(settings)
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError('Expected production security validation to fail')

    assert 'SECRET_ENCRYPTION_KEY' in message
    assert 'SECRET_STORE_BACKEND=env' in message
    assert 'DATABASE_URL' in message
    assert 'REDIS_URL' in message


def test_oidc_signer_key_persists_via_file(monkeypatch, tmp_path):
    key_path = tmp_path / 'oidc.pem'
    monkeypatch.setenv('OIDC_PRIVATE_KEY_B64', '')
    monkeypatch.setenv('OIDC_PRIVATE_KEY_PATH', str(key_path))
    monkeypatch.setenv('APP_ENV', 'dev')
    get_settings.cache_clear()
    get_signer.cache_clear()

    first = get_signer()
    first_private = base64.b64encode(first.private_pem).decode('ascii')

    get_signer.cache_clear()
    second = get_signer()
    second_private = base64.b64encode(second.private_pem).decode('ascii')

    assert key_path.exists()
    assert first_private == second_private
    get_signer.cache_clear()
    get_settings.cache_clear()
def test_auth_config_allows_frontend_origin(client):
    response = client.get('/auth/config', headers={'Origin': 'http://localhost:53000'})

    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'http://localhost:53000'
    assert response.headers['access-control-allow-credentials'] == 'true'


