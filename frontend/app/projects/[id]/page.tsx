'use client';

import Link from 'next/link';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { FormEvent, useEffect, useMemo, useState } from 'react';

import { Breadcrumbs } from '@/components/breadcrumbs';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { Pagination } from '@/components/pagination';
import { useSession } from '@/components/session-context';
import { StatusBadge } from '@/components/status-badge';
import { useToast } from '@/components/toast-provider';
import { hasRole } from '@/lib/auth';
import { apiDownload, apiJson } from '@/lib/api';
import { PROJECT_INTEGRATION_CATALOG } from '@/lib/constants';
import { compactId, formatDateTime, formatRisk } from '@/lib/format';
import type {
  AuditRun,
  EvidenceItem,
  FeatureFlags,
  Finding,
  Integration,
  PaginatedResponse,
  PricingPlan,
  Project,
  RemediationTask,
} from '@/lib/types';

type ProjectTab = 'overview' | 'runs' | 'findings' | 'remediation' | 'evidence' | 'integrations';

const RUNS_PAGE_SIZE = 10;
const EVIDENCE_PAGE_SIZE = 10;

export default function ProjectDetailPage() {
  const { session } = useSession();
  const { pushToast } = useToast();
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();

  const projectId = params.id;
  const canLaunchAudit = hasRole(session.role, ['org_admin', 'auditor']);
  const canUploadEvidence = hasRole(session.role, ['org_admin', 'auditor']);
  const canManageIntegrations = hasRole(session.role, ['org_admin', 'auditor']);

  const tabFromQuery = searchParams.get('tab');
  const tab: ProjectTab =
    tabFromQuery === 'overview' ||
    tabFromQuery === 'runs' ||
    tabFromQuery === 'findings' ||
    tabFromQuery === 'remediation' ||
    tabFromQuery === 'evidence' ||
    tabFromQuery === 'integrations'
      ? tabFromQuery
      : 'overview';

  const runFromQuery = searchParams.get('run');
  const [project, setProject] = useState<Project | null>(null);
  const [features, setFeatures] = useState<FeatureFlags | null>(null);
  const [plan, setPlan] = useState<PricingPlan | null>(null);
  const [runsPage, setRunsPage] = useState(1);
  const [runsData, setRunsData] = useState<PaginatedResponse<AuditRun>>({ items: [], page: 1, page_size: RUNS_PAGE_SIZE, total: 0 });
  const [selectedRunId, setSelectedRunId] = useState('');
  const [findings, setFindings] = useState<Finding[]>([]);
  const [tasks, setTasks] = useState<RemediationTask[]>([]);
  const [evidencePage, setEvidencePage] = useState(1);
  const [evidenceData, setEvidenceData] = useState<PaginatedResponse<EvidenceItem>>({
    items: [],
    page: 1,
    page_size: EVIDENCE_PAGE_SIZE,
    total: 0,
  });
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyRun, setBusyRun] = useState(false);
  const [error, setError] = useState('');
  const [verifyResult, setVerifyResult] = useState('');

  const [provider, setProvider] = useState<string>(PROJECT_INTEGRATION_CATALOG[0].provider);
  const [integrationName, setIntegrationName] = useState('');
  const [configJson, setConfigJson] = useState('{\n  "endpoint": "https://api.example.com"\n}');
  const [secretRef, setSecretRef] = useState('');
  const [createIntegrationBusy, setCreateIntegrationBusy] = useState(false);
  const [integrationToDelete, setIntegrationToDelete] = useState<Integration | null>(null);

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadMetadata, setUploadMetadata] = useState('{\n  "source": "manual"\n}');
  const [uploadItemType, setUploadItemType] = useState('manual_upload');
  const [uploadBusy, setUploadBusy] = useState(false);

  const selectedRun = useMemo(() => runsData.items.find((item) => item.id === selectedRunId) || runsData.items[0] || null, [runsData.items, selectedRunId]);

  function updateSearch(nextTab: ProjectTab, runId?: string) {
    const query = new URLSearchParams(searchParams.toString());
    query.set('tab', nextTab);
    if (runId) {
      query.set('run', runId);
    }
    router.replace(`/projects/${projectId}?${query.toString()}`);
  }

  function openTab(nextTab: ProjectTab) {
    updateSearch(nextTab, selectedRun?.id);
  }

  async function loadProject() {
    const projectPayload = await apiJson<Project>(`/projects/${projectId}`);
    setProject(projectPayload);
  }

  async function loadRuns(page: number) {
    const runsPayload = await apiJson<PaginatedResponse<AuditRun>>(
      `/projects/${projectId}/audit-runs?page=${page}&page_size=${RUNS_PAGE_SIZE}`,
    );
    setRunsData(runsPayload);
    if (runFromQuery && runsPayload.items.some((item) => item.id === runFromQuery)) {
      setSelectedRunId(runFromQuery);
    } else if (runsPayload.items[0]) {
      setSelectedRunId(runsPayload.items[0].id);
    } else {
      setSelectedRunId('');
    }
  }

  async function loadFindingsAndTasks(runId: string) {
    const [findingsPayload, tasksPayload] = await Promise.all([
      apiJson<Finding[]>(`/projects/${projectId}/audit-runs/${runId}/findings`),
      apiJson<RemediationTask[]>(`/projects/${projectId}/audit-runs/${runId}/remediation-tasks`),
    ]);
    setFindings(findingsPayload);
    setTasks(tasksPayload);
  }

  async function loadEvidence(page: number) {
    if (!session.orgId) {
      return;
    }
    const evidencePayload = await apiJson<PaginatedResponse<EvidenceItem>>(
      `/organizations/${session.orgId}/evidence?project_id=${projectId}&page=${page}&page_size=${EVIDENCE_PAGE_SIZE}`,
    );
    setEvidenceData(evidencePayload);
  }

  async function loadIntegrations() {
    const integrationPayload = await apiJson<Integration[]>(`/projects/${projectId}/integrations`);
    setIntegrations(integrationPayload);
  }

  useEffect(() => {
    if (!projectId || !session.orgId) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError('');

    Promise.all([
      loadProject(),
      loadRuns(runsPage),
      loadEvidence(evidencePage),
      loadIntegrations(),
      apiJson<FeatureFlags>('/enterprise/features'),
      apiJson<PricingPlan>(`/organizations/${session.orgId}/pricing-plan`),
    ])
      .then(([, , , , featuresPayload, planPayload]) => {
        if (!cancelled) {
          setFeatures(featuresPayload);
          setPlan(planPayload);
        }
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : 'Failed to load project';
        if (!cancelled) {
          setError(message);
          pushToast({ tone: 'error', title: 'Project load failed', message });
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
  }, [projectId, session.orgId, runsPage, evidencePage, pushToast]);

  useEffect(() => {
    if (!selectedRun?.id) {
      setFindings([]);
      setTasks([]);
      return;
    }
    loadFindingsAndTasks(selectedRun.id).catch((err) => {
      const message = err instanceof Error ? err.message : 'Failed to load findings';
      setError(message);
    });
  }, [selectedRun?.id, projectId]);

  async function runAudit() {
    setBusyRun(true);
    setError('');
    try {
      const payload = await apiJson<AuditRun>(`/projects/${projectId}/audit-runs`, {
        method: 'POST',
        body: JSON.stringify({ catalog_version: 'v1' }),
      });
      pushToast({ tone: 'success', title: 'Audit started', message: `Run ${compactId(payload.id)} queued.` });
      router.push(`/projects/${projectId}/runs/${payload.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not start audit';
      setError(message);
      pushToast({ tone: 'error', title: 'Run failed', message });
    } finally {
      setBusyRun(false);
    }
  }

  async function createIntegration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreateIntegrationBusy(true);
    setError('');
    try {
      const parsed = JSON.parse(configJson) as Record<string, unknown>;
      await apiJson<Integration>(`/projects/${projectId}/integrations`, {
        method: 'POST',
        body: JSON.stringify({
          provider,
          name: integrationName,
          config_json: parsed,
          secret_ref: secretRef || null,
          is_enabled: true,
        }),
      });
      setIntegrationName('');
      setSecretRef('');
      pushToast({ tone: 'success', title: 'Integration configured' });
      await loadIntegrations();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not configure integration';
      setError(message);
      pushToast({ tone: 'error', title: 'Integration error', message });
    } finally {
      setCreateIntegrationBusy(false);
    }
  }

  async function deleteIntegration() {
    if (!integrationToDelete) {
      return;
    }
    try {
      await apiJson<void>(`/integrations/${integrationToDelete.id}`, { method: 'DELETE' });
      pushToast({ tone: 'success', title: 'Integration removed' });
      setIntegrationToDelete(null);
      await loadIntegrations();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not delete integration';
      setError(message);
      pushToast({ tone: 'error', title: 'Delete failed', message });
    }
  }

  async function uploadEvidence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!uploadFile) {
      setError('Select a file before uploading.');
      return;
    }
    if (plan && uploadFile.size > plan.max_upload_bytes) {
      const mb = Math.floor(plan.max_upload_bytes / 1024 / 1024);
      setError(`File exceeds upload limit (${mb} MB).`);
      return;
    }
    setUploadBusy(true);
    setError('');
    try {
      JSON.parse(uploadMetadata);
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('item_type', uploadItemType);
      formData.append('metadata_json', uploadMetadata);
      if (selectedRun?.id) {
        formData.append('audit_run_id', selectedRun.id);
      }
      await apiJson<EvidenceItem>(`/projects/${projectId}/evidence/upload`, {
        method: 'POST',
        body: formData,
      });
      pushToast({ tone: 'success', title: 'Evidence uploaded' });
      setUploadFile(null);
      await loadEvidence(evidencePage);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
      pushToast({ tone: 'error', title: 'Upload failed', message });
    } finally {
      setUploadBusy(false);
    }
  }

  async function verifySignature(evidenceId: string) {
    if (!features?.feature_signing) {
      setVerifyResult('Signature verification is disabled by feature flag.');
      return;
    }
    try {
      const payload = await apiJson<{ valid: boolean; scan_status: string }>(`/evidence/${evidenceId}/verify-signature`);
      setVerifyResult(payload.valid ? 'Signature valid.' : 'Signature invalid.');
    } catch (err) {
      setVerifyResult(err instanceof Error ? err.message : 'Could not verify signature');
    }
  }

  const latestRun = runsData.items[0] || null;

  return (
    <section className="stack">
      <Breadcrumbs items={[{ label: 'Projects', href: '/projects' }, { label: project?.name || 'Project' }]} />
      <header className="page-header">
        <div>
          <h1 className="page-title">{project?.name || 'Project'}</h1>
          <p className="page-subtitle">{project?.description || 'No description available.'}</p>
        </div>
        <div className="actions">
          <Link href="/projects" className="button button-ghost">
            Back
          </Link>
          <button
            type="button"
            className="button button-primary"
            onClick={runAudit}
            disabled={!canLaunchAudit || busyRun}
            data-testid="project-run-one-click"
          >
            {busyRun ? 'Launching...' : 'Run 1-Click Audit'}
          </button>
        </div>
      </header>

      {error && <p className="error-text">{error}</p>}
      {loading && (
        <div className="stack">
          <div className="skeleton" style={{ height: 96 }} />
          <div className="skeleton" style={{ height: 240 }} />
        </div>
      )}

      {!loading && (
        <>
          <div className="tabs">
            <button type="button" className={`tab ${tab === 'overview' ? 'active' : ''}`} onClick={() => openTab('overview')}>
              Overview
            </button>
            <button type="button" className={`tab ${tab === 'runs' ? 'active' : ''}`} onClick={() => openTab('runs')}>
              Audit Runs
            </button>
            <button type="button" className={`tab ${tab === 'findings' ? 'active' : ''}`} onClick={() => openTab('findings')}>
              Findings
            </button>
            <button type="button" className={`tab ${tab === 'remediation' ? 'active' : ''}`} onClick={() => openTab('remediation')}>
              Remediation
            </button>
            <button type="button" className={`tab ${tab === 'evidence' ? 'active' : ''}`} onClick={() => openTab('evidence')}>
              Evidence
            </button>
            <button type="button" className={`tab ${tab === 'integrations' ? 'active' : ''}`} onClick={() => openTab('integrations')}>
              Integrations
            </button>
          </div>

          {tab === 'overview' && (
            <div className="grid-3">
              <article className="card">
                <p className="card-subtitle">Latest run status</p>
                <p className="kpi-value">{latestRun ? latestRun.status : 'none'}</p>
              </article>
              <article className="card">
                <p className="card-subtitle">Latest risk score</p>
                <p className="kpi-value">{formatRisk(latestRun?.risk_score)}</p>
              </article>
              <article className="card">
                <p className="card-subtitle">Evidence uploaded</p>
                <p className="kpi-value">{evidenceData.total}</p>
              </article>
              <article className="card" style={{ gridColumn: '1 / -1' }}>
                <h3 className="card-title">Quick actions</h3>
                <div className="actions" style={{ marginTop: 10 }}>
                  <button
                    type="button"
                    className="button button-primary"
                    onClick={runAudit}
                    disabled={!canLaunchAudit || busyRun}
                    data-testid="project-run-one-click-secondary"
                  >
                    Run 1-Click Audit
                  </button>
                  <button type="button" className="button button-secondary" onClick={() => openTab('evidence')}>
                    Upload evidence
                  </button>
                  <button type="button" className="button button-secondary" onClick={() => openTab('integrations')}>
                    Configure integrations
                  </button>
                </div>
              </article>
            </div>
          )}

          {tab === 'runs' && (
            <div className="card">
              {runsData.items.length === 0 ? (
                <div className="empty-state">
                  <strong>No runs yet.</strong>
                  <p>Run your first audit to generate findings and remediation.</p>
                </div>
              ) : (
                <>
                  <div className="table-wrap">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Run ID</th>
                          <th>Status</th>
                          <th>Risk</th>
                          <th>Updated</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {runsData.items.map((run) => (
                          <tr key={run.id}>
                            <td>{compactId(run.id)}</td>
                            <td>
                              <StatusBadge value={run.status} />
                            </td>
                            <td>{formatRisk(run.risk_score)}</td>
                            <td>{formatDateTime(run.updated_at)}</td>
                            <td>
                              <Link className="button button-ghost" href={`/projects/${projectId}/runs/${run.id}`}>
                                Open
                              </Link>
                              <button
                                type="button"
                                className="button button-secondary"
                                onClick={() => {
                                  setSelectedRunId(run.id);
                                  updateSearch('findings', run.id);
                                }}
                              >
                                View Findings
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <Pagination page={runsData.page} pageSize={runsData.page_size} total={runsData.total} onChange={setRunsPage} />
                </>
              )}
            </div>
          )}

          {tab === 'findings' && (
            <div className="card">
              {!selectedRun && (
                <div className="empty-state">
                  <strong>No run selected.</strong>
                  <p>Run an audit first.</p>
                </div>
              )}
              {selectedRun && findings.length === 0 && (
                <div className="empty-state">
                  <strong>No findings for this run.</strong>
                  <p>All controls passed or run is still in progress.</p>
                </div>
              )}
              {selectedRun && findings.length > 0 && (
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Severity</th>
                        <th>Status</th>
                        <th>Control</th>
                        <th>Evidence refs</th>
                        <th>Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {findings.map((finding) => (
                        <tr key={finding.id}>
                          <td><StatusBadge value={finding.severity} /></td>
                          <td>{finding.status}</td>
                          <td>{finding.control_id}</td>
                          <td>{finding.evidence_refs_json.length}</td>
                          <td>{finding.notes || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {tab === 'remediation' && (
            <div className="card">
              {!selectedRun && (
                <div className="empty-state">
                  <strong>No remediation tasks yet.</strong>
                  <p>Tasks appear after a run with findings.</p>
                </div>
              )}
              {selectedRun && tasks.length === 0 && (
                <div className="empty-state">
                  <strong>No remediation tasks for selected run.</strong>
                </div>
              )}
              {selectedRun && tasks.length > 0 && (
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Task</th>
                        <th>Owner</th>
                        <th>Due Date</th>
                        <th>SLA</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tasks.map((task) => (
                        <tr key={task.id}>
                          <td>
                            <strong>{task.title}</strong>
                            <p className="hint">{task.description}</p>
                          </td>
                          <td>{task.assignee_user_id || '-'}</td>
                          <td>{formatDateTime(task.due_date)}</td>
                          <td>{formatDateTime(task.sla_due_at)}</td>
                          <td>{task.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {tab === 'evidence' && (
            <div className="stack">
              <article className="card">
                <h3 className="card-title">Manual upload</h3>
                <p className="card-subtitle">Upload file + metadata JSON and attach it to this project.</p>
                {!canUploadEvidence && <p className="error-text">Your role cannot upload evidence.</p>}
                <form className="stack" onSubmit={uploadEvidence}>
                  <div className="row">
                    <div className="field">
                      <label className="label" htmlFor="evidence-file">
                        File
                      </label>
                      <input
                        id="evidence-file"
                        className="input"
                        type="file"
                        onChange={(event) => setUploadFile(event.target.files?.[0] || null)}
                        disabled={!canUploadEvidence}
                      />
                    </div>
                    <div className="field">
                      <label className="label" htmlFor="evidence-type">
                        Item type
                      </label>
                      <input
                        id="evidence-type"
                        className="input"
                        value={uploadItemType}
                        onChange={(event) => setUploadItemType(event.target.value)}
                        disabled={!canUploadEvidence}
                      />
                    </div>
                  </div>
                  <div className="field">
                    <label className="label" htmlFor="evidence-metadata">
                      metadata_json
                    </label>
                    <textarea
                      id="evidence-metadata"
                      className="textarea"
                      value={uploadMetadata}
                      onChange={(event) => setUploadMetadata(event.target.value)}
                      disabled={!canUploadEvidence}
                    />
                  </div>
                  <div className="actions">
                    <button className="button button-primary" type="submit" disabled={!canUploadEvidence || uploadBusy}>
                      {uploadBusy ? 'Uploading...' : 'Upload evidence'}
                    </button>
                    {plan && (
                      <span className="hint">Max upload {Math.floor(plan.max_upload_bytes / 1024 / 1024)} MB</span>
                    )}
                  </div>
                </form>
              </article>

              <article className="card">
                <h3 className="card-title">Evidence library</h3>
                {evidenceData.items.length === 0 && (
                  <div className="empty-state">
                    <strong>No evidence yet.</strong>
                  </div>
                )}
                {evidenceData.items.length > 0 && (
                  <>
                    <div className="table-wrap">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Type</th>
                            <th>Scan</th>
                            <th>Created</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {evidenceData.items.map((item) => (
                            <tr key={item.id}>
                              <td>{item.name}</td>
                              <td>{item.item_type}</td>
                              <td>
                                <StatusBadge value={item.scan_status === 'clean' ? 'clean' : 'quarantined'} />
                              </td>
                              <td>{formatDateTime(item.created_at)}</td>
                              <td>
                                <button
                                  type="button"
                                  className="button button-secondary"
                                  onClick={() => apiDownload(`/evidence/${item.id}/download`, item.name)}
                                  disabled={item.scan_status !== 'clean'}
                                >
                                  Download
                                </button>
                                <button
                                  type="button"
                                  className="button button-ghost"
                                  title={!features?.feature_signing ? 'feature_signing disabled' : 'Verify signature'}
                                  onClick={() => verifySignature(item.id)}
                                  disabled={!features?.feature_signing}
                                >
                                  Verify signature
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <Pagination
                      page={evidenceData.page}
                      pageSize={evidenceData.page_size}
                      total={evidenceData.total}
                      onChange={setEvidencePage}
                    />
                  </>
                )}
                {verifyResult && <p className="success-text">{verifyResult}</p>}
              </article>
            </div>
          )}

          {tab === 'integrations' && (
            <div className="grid-2">
              <article className="card">
                <h3 className="card-title">Configured integrations</h3>
                {integrations.length === 0 && (
                  <div className="empty-state">
                    <strong>No integrations yet.</strong>
                  </div>
                )}
                {integrations.length > 0 && (
                  <div className="table-wrap">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Provider</th>
                          <th>Name</th>
                          <th>Secret Ref</th>
                          <th>Status</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {integrations.map((integration) => (
                          <tr key={integration.id}>
                            <td>{integration.provider}</td>
                            <td>{integration.name}</td>
                            <td>{integration.secret_ref || '-'}</td>
                            <td>{integration.is_enabled ? 'enabled' : 'disabled'}</td>
                            <td>
                              <button
                                type="button"
                                className="button button-danger"
                                onClick={() => setIntegrationToDelete(integration)}
                                disabled={!canManageIntegrations}
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </article>

              <article className="card">
                <h3 className="card-title">Configure connector</h3>
                {!canManageIntegrations && <p className="error-text">Your role cannot configure integrations.</p>}
                <form className="stack" onSubmit={createIntegration}>
                  <div className="field">
                    <label className="label" htmlFor="provider">
                      Provider
                    </label>
                    <select
                      id="provider"
                      className="select"
                      value={provider}
                      onChange={(event) => setProvider(event.target.value)}
                      disabled={!canManageIntegrations}
                    >
                      {PROJECT_INTEGRATION_CATALOG.map((item) => (
                        <option key={item.provider} value={item.provider}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label className="label" htmlFor="integration-name">
                      Name
                    </label>
                    <input
                      id="integration-name"
                      className="input"
                      required
                      value={integrationName}
                      onChange={(event) => setIntegrationName(event.target.value)}
                      disabled={!canManageIntegrations}
                    />
                  </div>
                  <div className="field">
                    <label className="label" htmlFor="config-json">
                      config_json
                    </label>
                    <textarea
                      id="config-json"
                      className="textarea"
                      value={configJson}
                      onChange={(event) => setConfigJson(event.target.value)}
                      disabled={!canManageIntegrations}
                    />
                    <span className="hint">Do not include secrets in config_json.</span>
                  </div>
                  <div className="field">
                    <label className="label" htmlFor="secret-ref">
                      secret_ref (optional)
                    </label>
                    <input
                      id="secret-ref"
                      className="input"
                      value={secretRef}
                      onChange={(event) => setSecretRef(event.target.value)}
                      disabled={!canManageIntegrations}
                    />
                  </div>
                  <button className="button button-primary" type="submit" disabled={!canManageIntegrations || createIntegrationBusy}>
                    {createIntegrationBusy ? 'Saving...' : 'Save integration'}
                  </button>
                </form>
              </article>
            </div>
          )}
        </>
      )}

      <ConfirmDialog
        open={Boolean(integrationToDelete)}
        title="Delete integration"
        body={`Remove integration ${integrationToDelete?.name || ''}? This cannot be undone.`}
        confirmLabel="Delete"
        danger
        onCancel={() => setIntegrationToDelete(null)}
        onConfirm={deleteIntegration}
      />
    </section>
  );
}
