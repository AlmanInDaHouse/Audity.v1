from __future__ import annotations

import asyncio

from app import secret_store as secret_store_module
from app.signing import sign_manifest, verify_bundle


def test_ed25519_signing_key_persists_across_store_reloads(seeded_ids):
    async def _run() -> tuple[dict, dict]:
        first = await sign_manifest(seeded_ids['org_id'], {'artifact': 'first'})
        secret_store_module._secret_store = None
        second = await sign_manifest(seeded_ids['org_id'], {'artifact': 'second'})
        return first, second

    first_bundle, second_bundle = asyncio.run(_run())

    assert first_bundle['public_key'] == second_bundle['public_key']
    assert verify_bundle(first_bundle) is True
    assert verify_bundle(second_bundle) is True
