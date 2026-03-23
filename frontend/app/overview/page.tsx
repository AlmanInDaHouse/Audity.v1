'use client';

import Link from 'next/link';
import { AlertTriangle, CheckCircle2, Gauge, Layers3, ShieldAlert } from 'lucide-react';
import { useEffect, useState } from 'react';

import { StatusBadge } from '@/components/status-badge';
import { useSession } from '@/components/session-context';
import { useToast } from '@/components/toast-provider';
import { apiJson } from '@/lib/api';
import { compactId, formatDateTime, formatPercent, formatRisk } from '@/lib/format';
import type { OrganizationDashboard } from '@/lib/types';

export default function OverviewPage() {
  const { session } = useSession();
  const { pushToast } = useToast();
  const [dashboard, setDashboard] = useState<OrganizationDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!session.orgId) {
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError('');

    apiJson<OrganizationDashboard>(`/organizations/${session.orgId}/dashboard`)
      .then((payload) => {
        if (!cancelled) {
          setDashboard(payload);
        }
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : 'Failed to load overview';
        if (!cancelled) {
          setError(message);
          pushToast({ tone: 'error', title: 'Overview unavailable', message });
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [session.orgId, pushToast]);

  return (
    <section className="stack">
      <header className="hero-panel">
        <div className="hero-copy">
          <span className="eyebrow">Executive Overview</span>
          <h1 className="page-title">{dashboard?.org_name || 'Organization overview'}</h1>
          <p className="page-subtitle">
            Riesgo, cobertura y preparación operativa en una sola pantalla para defender el estado real del cliente.
          </p>
        </div>
        <div className="hero-actions">
          <Link href="/projects/new" className="button button-primary">
            Nuevo proyecto
          </Link>
          <Link href="/enterprise" className="button button-ghost">
            Ajustes enterprise
          </Link>
        </div>
      </header>

      {error && <p className="error-text">{error}</p>}

      {loading && (
        <div className="stack">
          <div className="skeleton" style={{ height: 120 }} />
          <div className="skeleton" style={{ height: 260 }} />
        </div>
      )}

      {!loading && dashboard && (
        <>
          <section className="metric-grid">
            <article className="card metric-card">
              <p className="card-subtitle">Readiness score</p>
              <p className="metric-value">{formatPercent(dashboard.readiness.score)}</p>
              <p className="hint">Basado en cobertura, seguridad, legal onboarding e integridad operativa.</p>
            </article>
            <article className="card metric-card">
              <p className="card-subtitle">Audit coverage</p>
              <p className="metric-value">{formatPercent(dashboard.summary.audit_coverage_pct)}</p>
              <p className="hint">{dashboard.summary.completed_runs} ejecuciones completadas.</p>
            </article>
            <article className="card metric-card">
              <p className="card-subtitle">Automation coverage</p>
              <p className="metric-value">{formatPercent(dashboard.summary.automation_coverage_pct)}</p>
              <p className="hint">{dashboard.summary.project_integrations} conectores de proyecto activos.</p>
            </article>
            <article className="card metric-card">
              <p className="card-subtitle">Evidence hygiene</p>
              <p className="metric-value">{formatPercent(dashboard.summary.evidence_hygiene_pct)}</p>
              <p className="hint">{dashboard.summary.quarantined_evidence} evidencias en cuarentena.</p>
            </article>
          </section>

          <section className="grid-2">
            <article className="card">
              <div className="section-head">
                <div>
                  <h2 className="card-title">Operating priorities</h2>
                  <p className="card-subtitle">Bloqueos reales para demos, venta enterprise y onboarding productivo.</p>
                </div>
              </div>
              <div className="signal-stack">
                <div className="signal-row">
                  <div className="signal-icon warning"><ShieldAlert size={16} /></div>
                  <div>
                    <strong>{dashboard.summary.critical_findings}</strong>
                    <p className="hint">Hallazgos críticos abiertos.</p>
                  </div>
                </div>
                <div className="signal-row">
                  <div className="signal-icon danger"><AlertTriangle size={16} /></div>
                  <div>
                    <strong>{dashboard.summary.overdue_tasks}</strong>
                    <p className="hint">Tareas de remediación fuera de SLA.</p>
                  </div>
                </div>
                <div className="signal-row">
                  <div className="signal-icon success"><CheckCircle2 size={16} /></div>
                  <div>
                    <strong>{dashboard.legal.dpa_status === 'signed' ? 'DPA firmado' : 'DPA pendiente'}</strong>
                    <p className="hint">El onboarding productivo sigue bloqueado hasta registrar el DPA.</p>
                  </div>
                </div>
                <div className="signal-row">
                  <div className="signal-icon info"><Gauge size={16} /></div>
                  <div>
                    <strong>{dashboard.summary.active_runs}</strong>
                    <p className="hint">Workflows de auditoría en ejecución.</p>
                  </div>
                </div>
              </div>
            </article>

            <article className="card">
              <div className="section-head">
                <div>
                  <h2 className="card-title">Commercial fit</h2>
                  <p className="card-subtitle">Capacidad usada, límites y módulos activables.</p>
                </div>
                <Layers3 size={18} />
              </div>
              <div className="stack">
                <div className="progress-panel">
                  <div className="progress-labels">
                    <span>Plan {dashboard.plan.plan_code}</span>
                    <strong>{formatPercent(dashboard.plan.project_usage_pct ?? dashboard.plan.asset_usage_pct)}</strong>
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{ width: `${Math.min(dashboard.plan.project_usage_pct ?? dashboard.plan.asset_usage_pct, 100)}%` }}
                    />
                  </div>
                  <p className="hint">
                    {dashboard.plan.projects_used ?? dashboard.plan.assets_used} de {dashboard.plan.max_projects ?? dashboard.plan.max_assets} proyectos usados
                  </p>
                </div>
                <div className="actions">
                  {dashboard.plan.modules_enabled.length === 0 && <span className="hint">No hay módulos premium activados.</span>}
                  {dashboard.plan.modules_enabled.map((module) => (
                    <span key={module} className="badge badge-completed">
                      {module}
                    </span>
                  ))}
                </div>
                <p className="hint">Límite de subida: {Math.floor(dashboard.plan.max_upload_bytes / 1024 / 1024)} MB por fichero.</p>
              </div>
            </article>
          </section>

          <section className="grid-2">
            <article className="card">
              <div className="section-head">
                <div>
                  <h2 className="card-title">Recent audit runs</h2>
                  <p className="card-subtitle">Actividad reciente con postura de control. El riesgo formal vive en el registro por proyecto.</p>
                </div>
              </div>
              {dashboard.recent_runs.length === 0 && (
                <div className="empty-state">
                  <strong>No audit runs yet.</strong>
                  <p>Lanza la primera auditoría para empezar a medir cobertura real.</p>
                </div>
              )}
              {dashboard.recent_runs.length > 0 && (
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Project</th>
                        <th>Status</th>
                        <th>Control posture score</th>
                        <th>Updated</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.recent_runs.map((run) => (
                        <tr key={run.id}>
                          <td>
                            <Link href={`/projects/${run.project_id}/runs/${run.id}`} style={{ color: '#0b6f66', fontWeight: 700 }}>
                              {run.project_name}
                            </Link>
                            <p className="hint">{compactId(run.id)}</p>
                          </td>
                          <td><StatusBadge value={run.status} /></td>
                          <td>{formatRisk(run.control_posture_score ?? run.risk_score)}</td>
                          <td>{formatDateTime(run.updated_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </article>

            <article className="card">
              <div className="section-head">
                <div>
                  <h2 className="card-title">Readiness checklist</h2>
                  <p className="card-subtitle">Qué falta para sostener una salida pre-GA creíble.</p>
                </div>
              </div>
              <div className="stack">
                {dashboard.readiness.items.map((item) => (
                  <div key={item.key} className="check-row">
                    <div className={`check-indicator ${item.ready ? 'ready' : 'attention'}`} />
                    <div>
                      <strong>{item.label}</strong>
                      <p className="hint">{item.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </article>
          </section>

          <article className="card">
            <div className="section-head">
              <div>
                <h2 className="card-title">Recent activity</h2>
                <p className="card-subtitle">Trazabilidad útil para demos y due diligence técnica.</p>
              </div>
            </div>
            {dashboard.recent_activity.length === 0 && (
              <div className="empty-state">
                <strong>No activity registered.</strong>
              </div>
            )}
            {dashboard.recent_activity.length > 0 && (
              <div className="activity-feed">
                {dashboard.recent_activity.map((item) => (
                  <div key={item.id} className="activity-row">
                    <div>
                      <strong>{item.action}</strong>
                      <p className="hint">
                        {item.entity_type} · {compactId(item.entity_id)}
                      </p>
                    </div>
                    <span className="hint">{formatDateTime(item.created_at)}</span>
                  </div>
                ))}
              </div>
            )}
          </article>
        </>
      )}
    </section>
  );
}
