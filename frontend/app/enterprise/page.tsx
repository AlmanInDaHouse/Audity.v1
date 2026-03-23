'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';

import { useSession } from '@/components/session-context';
import { useToast } from '@/components/toast-provider';
import { hasRole } from '@/lib/auth';
import { apiJson } from '@/lib/api';
import type { FeatureFlags, OrganizationLegalStatus, PricingPlan } from '@/lib/types';

type FlagKey = keyof FeatureFlags;

const FLAG_LABELS: Record<FlagKey, string> = {
  enterprise_features_enabled: 'Enterprise controls',
  feature_auth_enterprise: 'Enterprise IdP',
  feature_scim: 'SCIM',
  feature_secret_store: 'Secret store/Vault',
  feature_upload_av_scan: 'Antivirus scan',
  feature_signing: 'Evidence signing',
  feature_rbac_abac: 'RBAC/ABAC policies',
  feature_approvals: 'Finding approvals',
  feature_reporting_package: 'Reporting package',
  feature_pricing: 'Pricing controls',
};

export default function EnterprisePage() {
  const { session } = useSession();
  const { pushToast } = useToast();
  const canManage = hasRole(session.role, ['org_admin']);

  const [features, setFeatures] = useState<FeatureFlags | null>(null);
  const [planCode, setPlanCode] = useState('starter');
  const [maxAssets, setMaxAssets] = useState(50);
  const [maxUploadMb, setMaxUploadMb] = useState(20);
  const [modules, setModules] = useState('{\n  "approvals": false,\n  "reporting_package": false\n}');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [savingFlags, setSavingFlags] = useState(false);
  const [savingPlan, setSavingPlan] = useState(false);
  const [legal, setLegal] = useState<OrganizationLegalStatus | null>(null);
  const [dpaReference, setDpaReference] = useState('');
  const [savingLegal, setSavingLegal] = useState(false);

  useEffect(() => {
    if (!session.orgId) {
      return;
    }
    setLoading(true);
    setError('');
    Promise.all([
      apiJson<FeatureFlags>('/enterprise/features'),
      apiJson<PricingPlan>(`/organizations/${session.orgId}/pricing-plan`),
      apiJson<OrganizationLegalStatus & { org_id: string }>(`/organizations/${session.orgId}/legal/onboarding`),
    ])
      .then(([featurePayload, planPayload, legalPayload]) => {
        setFeatures(featurePayload);
        setPlanCode(planPayload.plan_code);
        setMaxAssets(planPayload.max_projects ?? planPayload.max_assets);
        setMaxUploadMb(Math.floor(planPayload.max_upload_bytes / 1024 / 1024));
        setModules(JSON.stringify(planPayload.modules_json, null, 2));
        setLegal(legalPayload);
        setDpaReference(legalPayload.dpa_reference || '');
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : 'Failed to load enterprise settings';
        setError(message);
      })
      .finally(() => setLoading(false));
  }, [session.orgId]);

  const readiness = useMemo(() => {
    return [
      { label: 'IdP', ok: Boolean(features?.feature_auth_enterprise) },
      { label: 'Vault', ok: Boolean(features?.feature_secret_store) },
      { label: 'AV scan', ok: Boolean(features?.feature_upload_av_scan) },
      { label: 'Observability', ok: Boolean(features?.enterprise_features_enabled) },
    ];
  }, [features]);

  async function saveFlags(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!features) {
      return;
    }
    setSavingFlags(true);
    setError('');
    try {
      const payload = await apiJson<FeatureFlags>('/enterprise/features', {
        method: 'PUT',
        body: JSON.stringify(features),
      });
      setFeatures(payload);
      pushToast({ tone: 'success', title: 'Feature flags saved' });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not save flags';
      setError(message);
      pushToast({ tone: 'error', title: 'Save failed', message });
    } finally {
      setSavingFlags(false);
    }
  }

  async function savePlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (maxAssets < 1 || maxUploadMb < 1) {
      setError('Plan limits must be positive values.');
      return;
    }
    setSavingPlan(true);
    setError('');
    try {
      const modulesJson = JSON.parse(modules) as Record<string, boolean>;
      await apiJson<PricingPlan>(`/organizations/${session.orgId}/pricing-plan`, {
        method: 'PUT',
        body: JSON.stringify({
          plan_code: planCode,
          max_projects: maxAssets,
          max_assets: maxAssets,
          max_upload_bytes: maxUploadMb * 1024 * 1024,
          modules_json: modulesJson,
        }),
      });
      pushToast({ tone: 'success', title: 'Pricing plan saved' });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not save plan';
      setError(message);
      pushToast({ tone: 'error', title: 'Plan save failed', message });
    } finally {
      setSavingPlan(false);
    }
  }

  async function registerDpa(status: 'requested' | 'signed') {
    setSavingLegal(true);
    setError('');
    try {
      const payload = await apiJson<OrganizationLegalStatus & { org_id: string }>(`/organizations/${session.orgId}/legal/dpa`, {
        method: 'PUT',
        body: JSON.stringify({
          status,
          reference: dpaReference || null,
        }),
      });
      setLegal(payload);
      pushToast({ tone: 'success', title: status === 'signed' ? 'DPA registrado' : 'DPA actualizado' });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not update DPA status';
      setError(message);
      pushToast({ tone: 'error', title: 'DPA update failed', message });
    } finally {
      setSavingLegal(false);
    }
  }

  async function completeOnboarding() {
    setSavingLegal(true);
    setError('');
    try {
      const payload = await apiJson<OrganizationLegalStatus & { org_id: string }>(
        `/organizations/${session.orgId}/legal/onboarding/complete`,
        { method: 'POST' },
      );
      setLegal(payload);
      pushToast({ tone: 'success', title: 'Onboarding completed' });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not complete onboarding';
      setError(message);
      pushToast({ tone: 'error', title: 'Onboarding blocked', message });
    } finally {
      setSavingLegal(false);
    }
  }

  if (!canManage) {
    return (
      <section className="stack">
        <header className="page-header">
          <div>
            <h1 className="page-title">Enterprise</h1>
            <p className="page-subtitle">Org admin permissions required.</p>
          </div>
        </header>
        <div className="card">
          <p className="error-text">Your role cannot edit enterprise controls.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="stack">
      <header className="page-header">
        <div>
          <h1 className="page-title">Enterprise Settings</h1>
          <p className="page-subtitle">Feature flags, pricing gates and environment readiness.</p>
        </div>
      </header>

      {error && <p className="error-text">{error}</p>}
      {loading && (
        <div className="stack">
          <div className="skeleton" style={{ height: 88 }} />
          <div className="skeleton" style={{ height: 180 }} />
        </div>
      )}

      {!loading && features && (
        <>
          {!features.enterprise_features_enabled && (
            <article className="card" style={{ background: '#fbf6ea', borderColor: '#eddcb6' }}>
              <h3 className="card-title">Upgrade required</h3>
              <p className="card-subtitle">Enterprise-only modules are disabled. You can still configure baseline pricing.</p>
            </article>
          )}

          <article className="card">
            <h2 className="card-title">Feature Flags</h2>
            <form className="stack" onSubmit={saveFlags}>
              {Object.keys(FLAG_LABELS).map((rawKey) => {
                const key = rawKey as FlagKey;
                return (
                  <label key={key} style={{ display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'space-between' }}>
                    <span>{FLAG_LABELS[key]}</span>
                    <input
                      type="checkbox"
                      checked={features[key]}
                      onChange={(event) => setFeatures((current) => (current ? { ...current, [key]: event.target.checked } : current))}
                    />
                  </label>
                );
              })}
              <div className="actions">
                <button type="submit" className="button button-primary" disabled={savingFlags}>
                  {savingFlags ? 'Saving...' : 'Save flags'}
                </button>
              </div>
            </form>
          </article>

          <article className="card">
            <h2 className="card-title">Pricing Plan</h2>
            <form className="stack" onSubmit={savePlan}>
              <div className="row">
                <div className="field">
                  <label className="label" htmlFor="plan-code">
                    Plan code
                  </label>
                  <input id="plan-code" className="input" value={planCode} onChange={(event) => setPlanCode(event.target.value)} />
                </div>
                <div className="field">
                  <label className="label" htmlFor="max-assets">
                    Max projects
                  </label>
                  <input
                    id="max-assets"
                    className="input"
                    type="number"
                    min={1}
                    value={maxAssets}
                    onChange={(event) => setMaxAssets(Number(event.target.value))}
                  />
                </div>
              </div>
              <div className="field">
                <label className="label" htmlFor="max-upload">
                  Max upload (MB)
                </label>
                <input
                  id="max-upload"
                  className="input"
                  type="number"
                  min={1}
                  value={maxUploadMb}
                  onChange={(event) => setMaxUploadMb(Number(event.target.value))}
                />
              </div>
              <div className="field">
                <label className="label" htmlFor="modules-json">
                  modules_json
                </label>
                <textarea id="modules-json" className="textarea" value={modules} onChange={(event) => setModules(event.target.value)} />
              </div>
              <button type="submit" className="button button-primary" disabled={savingPlan}>
                {savingPlan ? 'Saving...' : 'Save plan'}
              </button>
            </form>
          </article>

          <article className="card">
            <h2 className="card-title">Legal onboarding / DPA</h2>
            <div className="stack">
              <p className="hint">
                Estado actual: <strong>{legal?.dpa_status || 'pending'}</strong>. Onboarding: <strong>{legal?.onboarding_status || 'pending'}</strong>
              </p>
              <div className="field">
                <label className="label" htmlFor="dpa-reference">
                  DPA reference
                </label>
                <input
                  id="dpa-reference"
                  className="input"
                  value={dpaReference}
                  onChange={(event) => setDpaReference(event.target.value)}
                  placeholder="DPA-2026-001"
                />
              </div>
              <div className="actions">
                <button type="button" className="button button-secondary" disabled={savingLegal} onClick={() => registerDpa('requested')}>
                  {savingLegal ? 'Saving...' : 'Mark DPA requested'}
                </button>
                <button type="button" className="button button-primary" disabled={savingLegal} onClick={() => registerDpa('signed')}>
                  {savingLegal ? 'Saving...' : 'Register signed DPA'}
                </button>
                <button
                  type="button"
                  className="button button-ghost"
                  disabled={savingLegal || legal?.dpa_status !== 'signed'}
                  onClick={completeOnboarding}
                >
                  Complete onboarding
                </button>
              </div>
              <p className="hint">El producto bloquea el cierre de onboarding si el DPA no está firmado y registrado.</p>
            </div>
          </article>

          <article className="card">
            <h2 className="card-title">Health / Readiness</h2>
            <div className="grid-2">
              {readiness.map((item) => (
                <div key={item.label} className="card" style={{ boxShadow: 'none' }}>
                  <p className="card-subtitle">{item.label}</p>
                  <p className="kpi-value">{item.ok ? 'Enabled' : 'Missing'}</p>
                </div>
              ))}
            </div>
          </article>
        </>
      )}
    </section>
  );
}
