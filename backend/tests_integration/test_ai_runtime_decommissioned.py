from __future__ import annotations

import httpx
import pytest


async def _login(client: httpx.AsyncClient, base_url: str, email: str, org_id: str) -> str:
    response = await client.post(
        f'{base_url}/auth/mock/login',
        json={'email': email, 'org_id': org_id},
    )
    assert response.status_code == 200, response.text
    return response.json()['access_token']


@pytest.mark.asyncio
async def test_ai_orchestrator_routes_are_not_exposed(api_base_url, org_context):
    async with httpx.AsyncClient(timeout=30.0) as client:
        admin_token = await _login(client, api_base_url, org_context['users']['admin_a'], org_context['org_a_id'])
        headers = {'Authorization': f'Bearer {admin_token}'}

        create = await client.post(
            f'{api_base_url}/ai-orchestrator/runs',
            json={'project_id': org_context['project_a_id'], 'task_type': 'audit_fix'},
            headers=headers,
        )
        assert create.status_code == 404, create.text
