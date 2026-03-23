'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { Breadcrumbs } from '@/components/breadcrumbs';
import { useSession } from '@/components/session-context';
import { StatusBadge } from '@/components/status-badge';
import { useToast } from '@/components/toast-provider';
import { hasRole } from '@/lib/auth';
import { apiDownload, apiJson } from '@/lib/api';
import { formatDateTime, formatRisk } from '@/lib/format';
import type { AuditRun, FeatureFlags } from '@/lib/types';

type PackagePayload = {
  package_id: string;
  evidence_id: string;
  sha256: string;
};

const POLL_INTERVAL_MS = 3000;

export default function RunDetailPage() {
  const { session } = useSession();
  const { pushToast } = useToast();
  const params = useParams<{ id: string; run_id: string }>();
  const router = useRouter();

  const projectId = params.id;
  const runId = params.run_id;
  const canExportPackage = hasRole(session.role, ['org_admin', 'auditor', 'security_reviewer']);

  const [run, setRun] = useState<AuditRun | null>(null);
  const [features, setFeatures] = useState<FeatureFlags | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [exporting, setExporting] = useState(false);
  const [packageInfo, setPackageInfo] = useState<PackagePayload | null>(null);

  const currentStage = useMemo(() => String(run?.progress_json?.stage || 'queued'), [run?.progress_json]);
  const stageTimeline = ['queued', 'running', 'completed'];

  async function fetchRun() {
    const payload = await apiJson<AuditRun>(`/projects/${projectId}/audit-runs/${runId}`);
    setRun(payload);
    return payload;
  }

  useEffect(() => {
    let timer: number | null = null;
    let cancelled = false;
    setLoading(true);
    setError('');

    Promise.all([fetchRun(), apiJson<FeatureFlags>('/enterprise/features')])
      .then(([runPayload, featurePayload]) => {
        if (cancelled) {
          return;
        }
        setFeatures(featurePayload);
        if (runPayload.status === 'queued' || runPayload.status === 'running') {
          timer = window.setInterval(async () => {
            try {
              const live = await fetchRun();
              if (live.status === 'completed' || live.status === 'failed') {
                if (timer) {
                  window.clearInterval(timer);
                }
              }
            } catch {
              if (timer) {
                window.clearInterval(timer);
              }
            }
          }, POLL_INTERVAL_MS);
        }
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : 'Failed to load run';
        if (!cancelled) {
          setError(message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
      if (timer) {
        window.clearInterval(timer);
      }
    };
  }, [projectId, runId]);

  async function exportAuditorPackage() {
    setExporting(true);
    try {
      const payload = await apiJson<PackagePayload>(`/projects/${projectId}/audit-runs/${runId}/export-package`, {
        method: 'POST',
      });
      setPackageInfo(payload);
      pushToast({ tone: 'success', title: 'Auditor package ready' });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not export package';
      setError(message);
      pushToast({ tone: 'error', title: 'Export failed', message });
    } finally {
      setExporting(false);
    }
  }

  return (
    <section className="stack">
      <Breadcrumbs
        items={[
          { label: 'Projects', href: '/projects' },
          { label: `Project ${projectId}`, href: `/projects/${projectId}` },
          { label: `Run ${runId}` },
        ]}
      />
      <header className="page-header">
        <div>
          <h1 className="page-title">Audit Run</h1>
          <p className="page-subtitle">Live execution view with polling, run artifacts and control posture for this execution.</p>
        </div>
        <div className="actions">
          <button type="button" className="button button-ghost" onClick={() => router.push(`/projects/${projectId}`)}>
            Back to project
          </button>
        </div>
      </header>

      {error && <p className="error-text">{error}</p>}
      {loading && (
        <div className="stack">
          <div className="skeleton" style={{ height: 90 }} />
          <div className="skeleton" style={{ height: 220 }} />
        </div>
      )}

      {!loading && run && (
        <>
          <article className="card">
            <div className="grid-3">
              <div>
                <p className="card-subtitle">Status</p>
                <p className="kpi-value"><StatusBadge value={run.status} /></p>
              </div>
              <div>
                <p className="card-subtitle">Control posture score</p>
                <p className="kpi-value">{formatRisk(run.control_posture_score ?? run.risk_score)}</p>
                <p className="hint">This is run posture, not the formal risk register.</p>
              </div>
              <div>
                <p className="card-subtitle">Last update</p>
                <p className="kpi-value" style={{ fontSize: 18 }}>{formatDateTime(run.updated_at)}</p>
              </div>
            </div>
            <div className="actions" style={{ marginTop: 12 }}>
              <span className="badge badge-completed">Scope: {run.frameworks_json.join(', ')}</span>
              <span className="badge badge-completed">Catalog version: {run.catalog_version}</span>
              {run.catalog_version_id && <span className="badge badge-queued">Catalog id: {run.catalog_version_id.slice(0, 12)}</span>}
              {run.catalog_checksum && <span className="badge badge-queued">Catalog checksum: {run.catalog_checksum.slice(0, 12)}</span>}
            </div>
          </article>

          <article className="card">
            <h3 className="card-title">Timeline</h3>
            <div className="actions" style={{ marginTop: 12 }}>
              {stageTimeline.map((stage) => {
                const reached =
                  stage === currentStage ||
                  (stage === 'queued' && currentStage !== 'queued') ||
                  (stage === 'running' && (currentStage === 'completed' || currentStage === 'failed'));
                return <span key={stage} className={`badge ${reached ? 'badge-completed' : 'badge-queued'}`}>{stage}</span>;
              })}
              {run.status === 'failed' && <span className="badge badge-failed">failed</span>}
            </div>
          </article>

          <article className="card">
            <h3 className="card-title">Activities / logs</h3>
            <div className="grid-2" style={{ marginTop: 10 }}>
              <div>
                <p className="label">progress_json</p>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(run.progress_json, null, 2)}</pre>
              </div>
              <div>
                <p className="label">summary_json</p>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(run.summary_json, null, 2)}</pre>
              </div>
            </div>
          </article>

          <article className="card">
            <h3 className="card-title">Outputs</h3>
            <div className="actions" style={{ marginTop: 10 }}>
              <button
                type="button"
                className="button button-secondary"
                onClick={() => run.report_evidence_id && apiDownload(`/evidence/${run.report_evidence_id}/download`, `audit-report-${run.id}.pdf`)}
                disabled={!run.report_evidence_id}
              >
                Download PDF
              </button>
              <button
                type="button"
                className="button button-secondary"
                disabled={!canExportPackage || !features?.feature_reporting_package || run.status !== 'completed' || exporting}
                onClick={exportAuditorPackage}
                title={!features?.feature_reporting_package ? 'feature_reporting_package disabled' : 'Export auditor package'}
              >
                {exporting ? 'Exporting...' : 'Download Auditor Package'}
              </button>
              <Link href={`/projects/${projectId}?tab=findings&run=${run.id}`} className="button button-ghost">
                View Findings
              </Link>
              {packageInfo && (
                <button
                  type="button"
                  className="button button-ghost"
                  onClick={() => apiDownload(`/evidence/${packageInfo.evidence_id}/download`, `auditor-package-${run.id}.zip`)}
                >
                  Download ZIP
                </button>
              )}
            </div>
          </article>
        </>
      )}
    </section>
  );
}
