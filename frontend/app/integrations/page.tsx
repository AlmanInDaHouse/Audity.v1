'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';

import { useSession } from '@/components/session-context';
import { useToast } from '@/components/toast-provider';
import { hasRole } from '@/lib/auth';
import { apiJson } from '@/lib/api';
import { OUTBOUND_INTEGRATION_CATALOG } from '@/lib/constants';
import type { OutboundIntegration } from '@/lib/types';

export default function IntegrationsPage() {
  const { session } = useSession();
  const { pushToast } = useToast();
  const canConfigure = hasRole(session.role, ['org_admin']);

  const [items, setItems] = useState<OutboundIntegration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [kind, setKind] = useState<string>(OUTBOUND_INTEGRATION_CATALOG[0].kind);
  const [name, setName] = useState('');
  const [secretRef, setSecretRef] = useState('');
  const [configJson, setConfigJson] = useState('{\n  "webhook_url": "https://example.com/webhook"\n}');
  const [busy, setBusy] = useState(false);

  async function load() {
    const payload = await apiJson<OutboundIntegration[]>(`/organizations/${session.orgId}/outbound-integrations`);
    setItems(payload);
  }

  useEffect(() => {
    if (!session.orgId) {
      return;
    }
    setLoading(true);
    load()
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load integrations'))
      .finally(() => setLoading(false));
  }, [session.orgId]);

  const statusByKind = useMemo(() => {
    const map = new Map<string, 'configured' | 'error'>();
    items.forEach((item) => {
      map.set(item.kind, item.is_enabled ? 'configured' : 'error');
    });
    return map;
  }, [items]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const parsed = JSON.parse(configJson) as Record<string, unknown>;
      await apiJson<{ id: string }>(`/organizations/${session.orgId}/outbound-integrations`, {
        method: 'POST',
        body: JSON.stringify({
          kind,
          name,
          config_json: parsed,
          secret_ref: secretRef || null,
          is_enabled: true,
        }),
      });
      pushToast({ tone: 'success', title: 'Integration configured' });
      setName('');
      setSecretRef('');
      await load();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not configure integration';
      setError(message);
      pushToast({ tone: 'error', title: 'Configuration failed', message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="stack">
      <header className="page-header">
        <div>
          <h1 className="page-title">Integrations</h1>
          <p className="page-subtitle">Global outbound connectors for exports and notifications.</p>
        </div>
      </header>

      {error && <p className="error-text">{error}</p>}

      <article className="card">
        <h2 className="card-title">Catalog</h2>
        <div className="grid-3" style={{ marginTop: 10 }}>
          {OUTBOUND_INTEGRATION_CATALOG.map((item) => {
            const status = statusByKind.get(item.kind) || 'missing';
            return (
              <div key={item.kind} className="card" style={{ boxShadow: 'none' }}>
                <p className="card-title">{item.label}</p>
                <p className="hint">Kind: {item.kind}</p>
                <p className={`badge ${status === 'configured' ? 'badge-completed' : status === 'error' ? 'badge-failed' : 'badge-queued'}`}>
                  {status}
                </p>
              </div>
            );
          })}
        </div>
      </article>

      <article className="grid-2">
        <div className="card">
          <h2 className="card-title">Configured</h2>
          {loading && <div className="skeleton" style={{ height: 100 }} />}
          {!loading && items.length === 0 && (
            <div className="empty-state">
              <strong>No outbound integrations configured.</strong>
            </div>
          )}
          {!loading && items.length > 0 && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Kind</th>
                    <th>Secret ref</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td>{item.name}</td>
                      <td>{item.kind}</td>
                      <td>{item.secret_ref || '-'}</td>
                      <td>{item.is_enabled ? 'configured' : 'error'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card">
          <h2 className="card-title">Configure integration</h2>
          {!canConfigure && <p className="error-text">Only org admin can configure outbound integrations.</p>}
          <form className="stack" onSubmit={onSubmit}>
            <div className="field">
              <label className="label" htmlFor="out-kind">
                Kind
              </label>
              <select
                id="out-kind"
                className="select"
                value={kind}
                onChange={(event) => setKind(event.target.value)}
                disabled={!canConfigure}
              >
                {OUTBOUND_INTEGRATION_CATALOG.map((item) => (
                  <option key={item.kind} value={item.kind}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="label" htmlFor="out-name">
                Name
              </label>
              <input
                id="out-name"
                className="input"
                value={name}
                required
                onChange={(event) => setName(event.target.value)}
                disabled={!canConfigure}
              />
            </div>
            <div className="field">
              <label className="label" htmlFor="out-secret">
                secret_ref
              </label>
              <input
                id="out-secret"
                className="input"
                value={secretRef}
                onChange={(event) => setSecretRef(event.target.value)}
                disabled={!canConfigure}
              />
            </div>
            <div className="field">
              <label className="label" htmlFor="out-config">
                config_json
              </label>
              <textarea
                id="out-config"
                className="textarea"
                value={configJson}
                onChange={(event) => setConfigJson(event.target.value)}
                disabled={!canConfigure}
              />
            </div>
            <button type="submit" className="button button-primary" disabled={!canConfigure || busy}>
              {busy ? 'Saving...' : 'Save'}
            </button>
          </form>
        </div>
      </article>
    </section>
  );
}
