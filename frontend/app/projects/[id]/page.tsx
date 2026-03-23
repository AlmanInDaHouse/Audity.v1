'use client';

import Link from 'next/link';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';

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
  RiskOverview,
  RemediationTask,
} from '@/lib/types';

type ProjectTab = 'overview' | 'runs' | 'findings' | 'remediation' | 'risk' | 'evidence' | 'integrations';

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
  const canManageRisk = hasRole(session.role, ['org_admin', 'auditor']);

  const tabFromQuery = searchParams.get('tab');
  const tab: ProjectTab =
    tabFromQuery === 'overview' ||
    tabFromQuery === 'runs' ||
    tabFromQuery === 'findings' ||
    tabFromQuery === 'remediation' ||
    tabFromQuery === 'risk' ||
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
  const [riskData, setRiskData] = useState<RiskOverview | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);
  const [riskError, setRiskError] = useState('');
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

  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadMetadata, setUploadMetadata] = useState('{\n  "source": "manual"\n}');
  const [uploadItemType, setUploadItemType] = useState('manual_upload');
  const [uploadBusy, setUploadBusy] = useState(false);
  const fileUploadInputRef = useRef<HTMLInputElement | null>(null);
  const folderUploadInputRef = useRef<HTMLInputElement | null>(null);
  const [riskAssetName, setRiskAssetName] = useState('');
  const [riskAssetType, setRiskAssetType] = useState('information');
  const [riskThreatName, setRiskThreatName] = useState('');
  const [riskThreatCategory, setRiskThreatCategory] = useState('generic');
  const [riskSafeguardName, setRiskSafeguardName] = useState('');
  const [riskSafeguardStatus, setRiskSafeguardStatus] = useState('planned');
  const [riskAssessmentName, setRiskAssessmentName] = useState('');
  const [riskRelationSourceId, setRiskRelationSourceId] = useState('');
  const [riskRelationTargetId, setRiskRelationTargetId] = useState('');
  const [riskRelationType, setRiskRelationType] = useState('depends_on');
  const [riskScenarioTitle, setRiskScenarioTitle] = useState('');
  const [riskScenarioAssessmentId, setRiskScenarioAssessmentId] = useState('');
  const [riskScenarioAssetId, setRiskScenarioAssetId] = useState('');
  const [riskScenarioThreatId, setRiskScenarioThreatId] = useState('');
  const [riskScenarioSafeguardId, setRiskScenarioSafeguardId] = useState('');
  const [riskScenarioLikelihood, setRiskScenarioLikelihood] = useState('medium');
  const [riskScenarioImpact, setRiskScenarioImpact] = useState('medium');
  const [riskScenarioLevel, setRiskScenarioLevel] = useState('medium');
  const [riskScenarioDimensions, setRiskScenarioDimensions] = useState('{\n  "C": "medium"\n}');
  const [riskBusy, setRiskBusy] = useState(false);

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

  async function loadRisk() {
    setRiskLoading(true);
    try {
      const riskPayload = await apiJson<RiskOverview>(`/projects/${projectId}/risk`);
      setRiskData(riskPayload);
      setRiskError('');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load risk';
      setRiskError(message);
      throw err;
    } finally {
      setRiskLoading(false);
    }
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
    if (!projectId || !session.orgId || tab !== 'risk') {
      return;
    }
    let cancelled = false;
    loadRisk().catch((err) => {
      const message = err instanceof Error ? err.message : 'Failed to load risk';
      if (!cancelled) {
        pushToast({ tone: 'error', title: 'Risk load failed', message });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [projectId, session.orgId, tab, pushToast]);

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

  useEffect(() => {
    if (!riskData) {
      return;
    }
    if (!riskRelationSourceId && riskData.assets[0]) {
      setRiskRelationSourceId(riskData.assets[0].id);
    }
    if (!riskRelationTargetId && riskData.assets[1]) {
      setRiskRelationTargetId(riskData.assets[1].id);
    } else if (!riskRelationTargetId && riskData.assets[0]) {
      setRiskRelationTargetId(riskData.assets[0].id);
    }
    if (!riskScenarioAssessmentId && riskData.assessments[0]) {
      setRiskScenarioAssessmentId(riskData.assessments[0].id);
    }
    if (!riskScenarioAssetId && riskData.assets[0]) {
      setRiskScenarioAssetId(riskData.assets[0].id);
    }
    if (!riskScenarioThreatId && riskData.threats[0]) {
      setRiskScenarioThreatId(riskData.threats[0].id);
    }
    if (!riskScenarioSafeguardId && riskData.safeguards[0]) {
      setRiskScenarioSafeguardId(riskData.safeguards[0].id);
    }
  }, [
    riskData,
    riskRelationSourceId,
    riskRelationTargetId,
    riskScenarioAssessmentId,
    riskScenarioAssetId,
    riskScenarioThreatId,
    riskScenarioSafeguardId,
  ]);

  useEffect(() => {
    if (!folderUploadInputRef.current) {
      return;
    }
    folderUploadInputRef.current.setAttribute('webkitdirectory', '');
    folderUploadInputRef.current.setAttribute('directory', '');
  }, []);

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
    if (uploadFiles.length === 0) {
      setError('Select one or more files before uploading.');
      return;
    }
    if (plan) {
      const oversized = uploadFiles.find((file) => file.size > plan.max_upload_bytes);
      if (oversized) {
        const mb = Math.floor(plan.max_upload_bytes / 1024 / 1024);
        setError(`File ${oversized.name} exceeds upload limit (${mb} MB).`);
        return;
      }
    }
    setUploadBusy(true);
    setError('');
    try {
      const baseMetadata = JSON.parse(uploadMetadata) as Record<string, unknown>;
      const relativePaths = Object.fromEntries(
        uploadFiles
          .map((file) => {
            const relativePath = ((file as File & { webkitRelativePath?: string }).webkitRelativePath || '').trim();
            return relativePath ? [relativePath, relativePath] : null;
          })
          .filter((entry): entry is [string, string] => entry !== null),
      );
      const formData = new FormData();
      for (const file of uploadFiles) {
        const relativePath = ((file as File & { webkitRelativePath?: string }).webkitRelativePath || '').trim();
        formData.append('files', file, relativePath || file.name);
      }
      formData.append('item_type', uploadItemType);
      formData.append(
        'metadata_json',
        JSON.stringify(
          Object.keys(relativePaths).length > 0
            ? { ...baseMetadata, uploaded_from: 'directory', relative_paths: relativePaths }
            : baseMetadata,
        ),
      );
      if (selectedRun?.id) {
        formData.append('audit_run_id', selectedRun.id);
      }
      await apiJson<{ uploaded_count: number; items: EvidenceItem[] }>(`/projects/${projectId}/evidence/upload-batch`, {
        method: 'POST',
        body: formData,
      });
      pushToast({
        tone: 'success',
        title: uploadFiles.length > 1 ? 'Evidence batch uploaded' : 'Evidence uploaded',
        message: `${uploadFiles.length} file${uploadFiles.length === 1 ? '' : 's'} stored.`,
      });
      setUploadFiles([]);
      if (fileUploadInputRef.current) {
        fileUploadInputRef.current.value = '';
      }
      if (folderUploadInputRef.current) {
        folderUploadInputRef.current.value = '';
      }
      await loadEvidence(evidencePage);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
      pushToast({ tone: 'error', title: 'Upload failed', message });
    } finally {
      setUploadBusy(false);
    }
  }

  async function createRiskAsset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRiskBusy(true);
    setError('');
    try {
      await apiJson(`/projects/${projectId}/risk/assets`, {
        method: 'POST',
        body: JSON.stringify({ name: riskAssetName, asset_type: riskAssetType }),
      });
      setRiskAssetName('');
      pushToast({ tone: 'success', title: 'Risk asset created' });
      await loadRisk();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not create risk asset';
      setError(message);
      pushToast({ tone: 'error', title: 'Risk asset error', message });
    } finally {
      setRiskBusy(false);
    }
  }

  async function createRiskRelation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRiskBusy(true);
    setError('');
    try {
      await apiJson(`/projects/${projectId}/risk/asset-relations`, {
        method: 'POST',
        body: JSON.stringify({
          source_asset_id: riskRelationSourceId,
          target_asset_id: riskRelationTargetId,
          relation_type: riskRelationType,
        }),
      });
      pushToast({ tone: 'success', title: 'Risk relation created' });
      await loadRisk();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not create risk relation';
      setError(message);
      pushToast({ tone: 'error', title: 'Risk relation error', message });
    } finally {
      setRiskBusy(false);
    }
  }

  async function createRiskThreat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRiskBusy(true);
    setError('');
    try {
      await apiJson(`/projects/${projectId}/risk/threats`, {
        method: 'POST',
        body: JSON.stringify({ name: riskThreatName, category: riskThreatCategory }),
      });
      setRiskThreatName('');
      pushToast({ tone: 'success', title: 'Risk threat created' });
      await loadRisk();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not create risk threat';
      setError(message);
      pushToast({ tone: 'error', title: 'Risk threat error', message });
    } finally {
      setRiskBusy(false);
    }
  }

  async function createRiskSafeguard(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRiskBusy(true);
    setError('');
    try {
      await apiJson(`/projects/${projectId}/risk/safeguards`, {
        method: 'POST',
        body: JSON.stringify({ name: riskSafeguardName, status: riskSafeguardStatus }),
      });
      setRiskSafeguardName('');
      pushToast({ tone: 'success', title: 'Risk safeguard created' });
      await loadRisk();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not create risk safeguard';
      setError(message);
      pushToast({ tone: 'error', title: 'Risk safeguard error', message });
    } finally {
      setRiskBusy(false);
    }
  }

  async function createRiskAssessment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRiskBusy(true);
    setError('');
    try {
      await apiJson(`/projects/${projectId}/risk/assessments`, {
        method: 'POST',
        body: JSON.stringify({ name: riskAssessmentName, methodology: 'manual-v1', status: 'draft' }),
      });
      setRiskAssessmentName('');
      pushToast({ tone: 'success', title: 'Risk assessment created' });
      await loadRisk();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not create risk assessment';
      setError(message);
      pushToast({ tone: 'error', title: 'Risk assessment error', message });
    } finally {
      setRiskBusy(false);
    }
  }

  async function createRiskScenario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRiskBusy(true);
    setError('');
    try {
      const dimensionValues = JSON.parse(riskScenarioDimensions) as Record<string, string>;
      await apiJson(`/projects/${projectId}/risk/scenarios`, {
        method: 'POST',
        body: JSON.stringify({
          assessment_id: riskScenarioAssessmentId,
          asset_id: riskScenarioAssetId || null,
          threat_id: riskScenarioThreatId || null,
          safeguard_id: riskScenarioSafeguardId || null,
          title: riskScenarioTitle,
          likelihood: riskScenarioLikelihood,
          impact: riskScenarioImpact,
          risk_level: riskScenarioLevel,
          dimension_values_json: dimensionValues,
        }),
      });
      setRiskScenarioTitle('');
      setRiskScenarioDimensions('{\n  "C": "medium"\n}');
      pushToast({ tone: 'success', title: 'Risk scenario created' });
      await loadRisk();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not create risk scenario';
      setError(message);
      pushToast({ tone: 'error', title: 'Risk scenario error', message });
    } finally {
      setRiskBusy(false);
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
  const latestControlPostureScore = latestRun?.control_posture_score ?? latestRun?.risk_score ?? null;
  const riskDimensions = riskData?.dimensions || [];
  const riskAssets = riskData?.assets || [];
  const riskRelations = riskData?.asset_relations || [];
  const riskThreats = riskData?.threats || [];
  const riskSafeguards = riskData?.safeguards || [];
  const riskAssessments = riskData?.assessments || [];
  const riskScenarios = riskData?.scenarios || [];
  const riskRegister = riskData?.risk_register || [];
  const evaluatedRiskScenarios = riskRegister.filter((entry) => entry.latest_evaluation !== null).length;

  return (
    <section className="stack">
      <Breadcrumbs items={[{ label: 'Projects', href: '/projects' }, { label: project?.name || 'Project' }]} />
      <header className="page-header">
        <div>
          <h1 className="page-title">{project?.name || 'Project'}</h1>
          <p className="page-subtitle">{project?.description || 'No description available.'}</p>
          {project?.frameworks?.length ? (
            <p className="hint">Scope: {project.frameworks.join(', ')}</p>
          ) : null}
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
            <button type="button" className={`tab ${tab === 'risk' ? 'active' : ''}`} onClick={() => openTab('risk')}>
              Risk
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
                <p className="card-subtitle">Latest control posture score</p>
                <p className="kpi-value">{formatRisk(latestControlPostureScore)}</p>
                <p className="hint">Execution posture from the latest audit run. Formal risk remains separate in the Risk tab.</p>
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
                          <th>Control posture score</th>
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
                            <td>{formatRisk(run.control_posture_score ?? run.risk_score)}</td>
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

          {tab === 'risk' && (
            <div className="stack">
              {riskError && <p className="error-text">{riskError}</p>}
              {riskLoading && (
                <div className="stack">
                  <div className="skeleton" style={{ height: 96 }} />
                  <div className="skeleton" style={{ height: 240 }} />
                </div>
              )}
              {!riskLoading && (
                <>
              <div className="grid-3">
                <article className="card">
                  <p className="card-subtitle">Dimensions</p>
                  <p className="kpi-value">{riskDimensions.length}</p>
                </article>
                <article className="card">
                  <p className="card-subtitle">Register entries</p>
                  <p className="kpi-value">{riskRegister.length}</p>
                </article>
                <article className="card">
                  <p className="card-subtitle">Evaluated scenarios</p>
                  <p className="kpi-value">{evaluatedRiskScenarios}</p>
                </article>
              </div>

              <article className="card" data-testid="formal-risk-register">
                <div className="section-head">
                  <div>
                    <h3 className="card-title">Formal risk register</h3>
                    <p className="card-subtitle">
                      Versioned evaluations, treatments and traceability. Audit runs keep control posture separate.
                    </p>
                  </div>
                </div>
                {riskRegister.length === 0 ? (
                  <div className="empty-state">
                    <strong>No formal risk scenarios yet.</strong>
                    <p>Create an assessment and at least one scenario to populate the register.</p>
                  </div>
                ) : (
                  <div className="table-wrap">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Scenario</th>
                          <th>Inherent</th>
                          <th>Residual</th>
                          <th>Evaluations</th>
                          <th>Treatments</th>
                          <th>Last evaluated</th>
                        </tr>
                      </thead>
                      <tbody>
                        {riskRegister.map((entry) => (
                          <tr key={entry.scenario.id}>
                            <td>
                              <strong>{entry.scenario.title}</strong>
                              <p className="hint">{entry.scenario.risk_level ? `Declared level: ${entry.scenario.risk_level}` : 'Scenario declared without baseline level.'}</p>
                            </td>
                            <td>{entry.latest_evaluation ? entry.latest_evaluation.inherent_level : '-'}</td>
                            <td>{entry.latest_evaluation ? entry.latest_evaluation.residual_level : '-'}</td>
                            <td>{entry.traceability.evaluation_versions}</td>
                            <td>
                              {entry.traceability.treatments_total}
                              <p className="hint">
                                {entry.traceability.implemented_treatments} implemented / {entry.traceability.accepted_treatments} accepted
                              </p>
                            </td>
                            <td>{formatDateTime(entry.traceability.last_evaluated_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </article>

              <div className="grid-2">
                <article className="card">
                  <h3 className="card-title">Security dimensions</h3>
                  <div className="table-wrap">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Code</th>
                          <th>Name</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {riskDimensions.map((dimension) => (
                          <tr key={dimension.id}>
                            <td>{dimension.code}</td>
                            <td>{dimension.name}</td>
                            <td>{dimension.is_active ? 'active' : 'inactive'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </article>

                <article className="card">
                  <h3 className="card-title">Assessments</h3>
                  {riskAssessments.length === 0 ? (
                    <div className="empty-state">
                      <strong>No assessments yet.</strong>
                    </div>
                  ) : (
                    <div className="table-wrap">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Methodology</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {riskAssessments.map((assessment) => (
                            <tr key={assessment.id}>
                              <td>{assessment.name}</td>
                              <td>{assessment.methodology}</td>
                              <td>{assessment.status}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <form className="stack" onSubmit={createRiskAssessment} style={{ marginTop: 16 }}>
                    <div className="field">
                      <label className="label" htmlFor="risk-assessment-name">
                        Assessment name
                      </label>
                      <input
                        id="risk-assessment-name"
                        className="input"
                        value={riskAssessmentName}
                        onChange={(event) => setRiskAssessmentName(event.target.value)}
                        disabled={!canManageRisk || riskBusy}
                        required
                      />
                    </div>
                    <button className="button button-primary" type="submit" disabled={!canManageRisk || riskBusy}>
                      {riskBusy ? 'Saving...' : 'Create assessment'}
                    </button>
                  </form>
                </article>

                <article className="card">
                  <h3 className="card-title">Assets</h3>
                  {riskAssets.length === 0 ? (
                    <div className="empty-state">
                      <strong>No assets yet.</strong>
                    </div>
                  ) : (
                    <div className="table-wrap">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Type</th>
                            <th>Criticality</th>
                          </tr>
                        </thead>
                        <tbody>
                          {riskAssets.map((asset) => (
                            <tr key={asset.id}>
                              <td>{asset.name}</td>
                              <td>{asset.asset_type}</td>
                              <td>{asset.criticality}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <form className="stack" onSubmit={createRiskAsset} style={{ marginTop: 16 }}>
                    <div className="row">
                      <div className="field">
                        <label className="label" htmlFor="risk-asset-name">
                          Asset name
                        </label>
                        <input
                          id="risk-asset-name"
                          className="input"
                          value={riskAssetName}
                          onChange={(event) => setRiskAssetName(event.target.value)}
                          disabled={!canManageRisk || riskBusy}
                          required
                        />
                      </div>
                      <div className="field">
                        <label className="label" htmlFor="risk-asset-type">
                          Type
                        </label>
                        <input
                          id="risk-asset-type"
                          className="input"
                          value={riskAssetType}
                          onChange={(event) => setRiskAssetType(event.target.value)}
                          disabled={!canManageRisk || riskBusy}
                        />
                      </div>
                    </div>
                    <button className="button button-primary" type="submit" disabled={!canManageRisk || riskBusy}>
                      {riskBusy ? 'Saving...' : 'Add asset'}
                    </button>
                  </form>
                </article>

                <article className="card">
                  <h3 className="card-title">Asset relations</h3>
                  {riskRelations.length === 0 ? (
                    <div className="empty-state">
                      <strong>No asset relations yet.</strong>
                    </div>
                  ) : (
                    <div className="table-wrap">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Source</th>
                            <th>Target</th>
                            <th>Relation</th>
                          </tr>
                        </thead>
                        <tbody>
                          {riskRelations.map((relation) => (
                            <tr key={relation.id}>
                              <td>{riskAssets.find((asset) => asset.id === relation.source_asset_id)?.name || compactId(relation.source_asset_id)}</td>
                              <td>{riskAssets.find((asset) => asset.id === relation.target_asset_id)?.name || compactId(relation.target_asset_id)}</td>
                              <td>{relation.relation_type}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <form className="stack" onSubmit={createRiskRelation} style={{ marginTop: 16 }}>
                    <div className="row">
                      <div className="field">
                        <label className="label" htmlFor="risk-relation-source">
                          Source asset
                        </label>
                        <select
                          id="risk-relation-source"
                          className="select"
                          value={riskRelationSourceId}
                          onChange={(event) => setRiskRelationSourceId(event.target.value)}
                          disabled={!canManageRisk || riskBusy || riskAssets.length === 0}
                        >
                          <option value="">Select asset</option>
                          {riskAssets.map((asset) => (
                            <option key={asset.id} value={asset.id}>
                              {asset.name}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="field">
                        <label className="label" htmlFor="risk-relation-target">
                          Target asset
                        </label>
                        <select
                          id="risk-relation-target"
                          className="select"
                          value={riskRelationTargetId}
                          onChange={(event) => setRiskRelationTargetId(event.target.value)}
                          disabled={!canManageRisk || riskBusy || riskAssets.length === 0}
                        >
                          <option value="">Select asset</option>
                          {riskAssets.map((asset) => (
                            <option key={asset.id} value={asset.id}>
                              {asset.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div className="field">
                      <label className="label" htmlFor="risk-relation-type">
                        Relation type
                      </label>
                      <input
                        id="risk-relation-type"
                        className="input"
                        value={riskRelationType}
                        onChange={(event) => setRiskRelationType(event.target.value)}
                        disabled={!canManageRisk || riskBusy}
                      />
                    </div>
                    <button
                      className="button button-primary"
                      type="submit"
                      disabled={!canManageRisk || riskBusy || !riskRelationSourceId || !riskRelationTargetId}
                    >
                      {riskBusy ? 'Saving...' : 'Add relation'}
                    </button>
                  </form>
                </article>

                <article className="card">
                  <h3 className="card-title">Threats</h3>
                  {riskThreats.length === 0 ? (
                    <div className="empty-state">
                      <strong>No threats yet.</strong>
                    </div>
                  ) : (
                    <div className="table-wrap">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Category</th>
                          </tr>
                        </thead>
                        <tbody>
                          {riskThreats.map((threat) => (
                            <tr key={threat.id}>
                              <td>{threat.name}</td>
                              <td>{threat.category}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <form className="stack" onSubmit={createRiskThreat} style={{ marginTop: 16 }}>
                    <div className="row">
                      <div className="field">
                        <label className="label" htmlFor="risk-threat-name">
                          Threat name
                        </label>
                        <input
                          id="risk-threat-name"
                          className="input"
                          value={riskThreatName}
                          onChange={(event) => setRiskThreatName(event.target.value)}
                          disabled={!canManageRisk || riskBusy}
                          required
                        />
                      </div>
                      <div className="field">
                        <label className="label" htmlFor="risk-threat-category">
                          Category
                        </label>
                        <input
                          id="risk-threat-category"
                          className="input"
                          value={riskThreatCategory}
                          onChange={(event) => setRiskThreatCategory(event.target.value)}
                          disabled={!canManageRisk || riskBusy}
                        />
                      </div>
                    </div>
                    <button className="button button-primary" type="submit" disabled={!canManageRisk || riskBusy}>
                      {riskBusy ? 'Saving...' : 'Add threat'}
                    </button>
                  </form>
                </article>

                <article className="card">
                  <h3 className="card-title">Safeguards</h3>
                  {riskSafeguards.length === 0 ? (
                    <div className="empty-state">
                      <strong>No safeguards yet.</strong>
                    </div>
                  ) : (
                    <div className="table-wrap">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {riskSafeguards.map((safeguard) => (
                            <tr key={safeguard.id}>
                              <td>{safeguard.name}</td>
                              <td>{safeguard.status}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <form className="stack" onSubmit={createRiskSafeguard} style={{ marginTop: 16 }}>
                    <div className="row">
                      <div className="field">
                        <label className="label" htmlFor="risk-safeguard-name">
                          Safeguard name
                        </label>
                        <input
                          id="risk-safeguard-name"
                          className="input"
                          value={riskSafeguardName}
                          onChange={(event) => setRiskSafeguardName(event.target.value)}
                          disabled={!canManageRisk || riskBusy}
                          required
                        />
                      </div>
                      <div className="field">
                        <label className="label" htmlFor="risk-safeguard-status">
                          Status
                        </label>
                        <input
                          id="risk-safeguard-status"
                          className="input"
                          value={riskSafeguardStatus}
                          onChange={(event) => setRiskSafeguardStatus(event.target.value)}
                          disabled={!canManageRisk || riskBusy}
                        />
                      </div>
                    </div>
                    <button className="button button-primary" type="submit" disabled={!canManageRisk || riskBusy}>
                      {riskBusy ? 'Saving...' : 'Add safeguard'}
                    </button>
                  </form>
                </article>
              </div>

              <article className="card">
                <h3 className="card-title">Scenarios</h3>
                {riskScenarios.length === 0 ? (
                  <div className="empty-state">
                    <strong>No risk scenarios yet.</strong>
                  </div>
                ) : (
                  <div className="table-wrap">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Title</th>
                          <th>Assessment</th>
                          <th>Asset</th>
                          <th>Threat</th>
                          <th>Level</th>
                        </tr>
                      </thead>
                      <tbody>
                        {riskScenarios.map((scenario) => (
                          <tr key={scenario.id}>
                            <td>{scenario.title}</td>
                            <td>{riskAssessments.find((assessment) => assessment.id === scenario.assessment_id)?.name || compactId(scenario.assessment_id)}</td>
                            <td>{riskAssets.find((asset) => asset.id === scenario.asset_id)?.name || '-'}</td>
                            <td>{riskThreats.find((threat) => threat.id === scenario.threat_id)?.name || '-'}</td>
                            <td>{scenario.risk_level || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                <form className="stack" onSubmit={createRiskScenario} style={{ marginTop: 16 }}>
                  <div className="row">
                    <div className="field">
                      <label className="label" htmlFor="risk-scenario-title">
                        Scenario title
                      </label>
                      <input
                        id="risk-scenario-title"
                        className="input"
                        value={riskScenarioTitle}
                        onChange={(event) => setRiskScenarioTitle(event.target.value)}
                        disabled={!canManageRisk || riskBusy}
                        required
                      />
                    </div>
                    <div className="field">
                      <label className="label" htmlFor="risk-scenario-assessment">
                        Assessment
                      </label>
                      <select
                        id="risk-scenario-assessment"
                        className="select"
                        value={riskScenarioAssessmentId}
                        onChange={(event) => setRiskScenarioAssessmentId(event.target.value)}
                        disabled={!canManageRisk || riskBusy || riskAssessments.length === 0}
                      >
                        <option value="">Select assessment</option>
                        {riskAssessments.map((assessment) => (
                          <option key={assessment.id} value={assessment.id}>
                            {assessment.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="row">
                    <div className="field">
                      <label className="label" htmlFor="risk-scenario-asset">
                        Asset
                      </label>
                      <select
                        id="risk-scenario-asset"
                        className="select"
                        value={riskScenarioAssetId}
                        onChange={(event) => setRiskScenarioAssetId(event.target.value)}
                        disabled={!canManageRisk || riskBusy || riskAssets.length === 0}
                      >
                        <option value="">Optional</option>
                        {riskAssets.map((asset) => (
                          <option key={asset.id} value={asset.id}>
                            {asset.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="field">
                      <label className="label" htmlFor="risk-scenario-threat">
                        Threat
                      </label>
                      <select
                        id="risk-scenario-threat"
                        className="select"
                        value={riskScenarioThreatId}
                        onChange={(event) => setRiskScenarioThreatId(event.target.value)}
                        disabled={!canManageRisk || riskBusy || riskThreats.length === 0}
                      >
                        <option value="">Optional</option>
                        {riskThreats.map((threat) => (
                          <option key={threat.id} value={threat.id}>
                            {threat.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="field">
                      <label className="label" htmlFor="risk-scenario-safeguard">
                        Safeguard
                      </label>
                      <select
                        id="risk-scenario-safeguard"
                        className="select"
                        value={riskScenarioSafeguardId}
                        onChange={(event) => setRiskScenarioSafeguardId(event.target.value)}
                        disabled={!canManageRisk || riskBusy || riskSafeguards.length === 0}
                      >
                        <option value="">Optional</option>
                        {riskSafeguards.map((safeguard) => (
                          <option key={safeguard.id} value={safeguard.id}>
                            {safeguard.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="row">
                    <div className="field">
                      <label className="label" htmlFor="risk-scenario-likelihood">
                        Likelihood
                      </label>
                      <input
                        id="risk-scenario-likelihood"
                        className="input"
                        value={riskScenarioLikelihood}
                        onChange={(event) => setRiskScenarioLikelihood(event.target.value)}
                        disabled={!canManageRisk || riskBusy}
                      />
                    </div>
                    <div className="field">
                      <label className="label" htmlFor="risk-scenario-impact">
                        Impact
                      </label>
                      <input
                        id="risk-scenario-impact"
                        className="input"
                        value={riskScenarioImpact}
                        onChange={(event) => setRiskScenarioImpact(event.target.value)}
                        disabled={!canManageRisk || riskBusy}
                      />
                    </div>
                    <div className="field">
                      <label className="label" htmlFor="risk-scenario-level">
                        Risk level
                      </label>
                      <input
                        id="risk-scenario-level"
                        className="input"
                        value={riskScenarioLevel}
                        onChange={(event) => setRiskScenarioLevel(event.target.value)}
                        disabled={!canManageRisk || riskBusy}
                      />
                    </div>
                  </div>
                  <div className="field">
                    <label className="label" htmlFor="risk-scenario-dimensions">
                      dimension_values_json
                    </label>
                    <textarea
                      id="risk-scenario-dimensions"
                      className="textarea"
                      value={riskScenarioDimensions}
                      onChange={(event) => setRiskScenarioDimensions(event.target.value)}
                      disabled={!canManageRisk || riskBusy}
                    />
                  </div>
                  <button
                    className="button button-primary"
                    type="submit"
                    disabled={!canManageRisk || riskBusy || !riskScenarioAssessmentId}
                  >
                    {riskBusy ? 'Saving...' : 'Create scenario'}
                  </button>
                </form>
              </article>
                </>
              )}
            </div>
          )}

          {tab === 'evidence' && (
            <div className="stack">
              <article className="card">
                <h3 className="card-title">Manual upload</h3>
                <p className="card-subtitle">Upload files or a folder and attach them to this project. Folder uploads preserve relative paths in metadata.</p>
                {!canUploadEvidence && <p className="error-text">Your role cannot upload evidence.</p>}
                <form className="stack" onSubmit={uploadEvidence}>
                  <div className="row">
                    <div className="field">
                      <label className="label" htmlFor="evidence-file">
                        Files
                      </label>
                      <input
                        id="evidence-file"
                        className="input"
                        type="file"
                        multiple
                        ref={fileUploadInputRef}
                        onChange={(event) => setUploadFiles(Array.from(event.target.files || []))}
                        disabled={!canUploadEvidence || uploadBusy}
                      />
                      <p className="hint">You can select multiple files here, or choose a folder below.</p>
                    </div>
                    <div className="field">
                      <label className="label" htmlFor="evidence-folder">
                        Folder
                      </label>
                      <input
                        id="evidence-folder"
                        className="input"
                        type="file"
                        multiple
                        ref={folderUploadInputRef}
                        onChange={(event) => setUploadFiles(Array.from(event.target.files || []))}
                        disabled={!canUploadEvidence || uploadBusy}
                      />
                      <p className="hint">Browser support uses directory selection and uploads each file separately.</p>
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
                        disabled={!canUploadEvidence || uploadBusy}
                      />
                    </div>
                  </div>
                  {uploadFiles.length > 0 && (
                    <div className="card" style={{ boxShadow: 'none' }}>
                      <p className="card-subtitle">Selection</p>
                      <p className="hint">{uploadFiles.length} file{uploadFiles.length === 1 ? '' : 's'} ready for upload.</p>
                      <div className="stack" style={{ gap: 6 }}>
                        {uploadFiles.slice(0, 5).map((file) => {
                          const relativePath = ((file as File & { webkitRelativePath?: string }).webkitRelativePath || '').trim();
                          return (
                            <p key={`${file.name}-${file.size}-${relativePath}`} className="hint" style={{ margin: 0 }}>
                              {relativePath || file.name}
                            </p>
                          );
                        })}
                        {uploadFiles.length > 5 && (
                          <p className="hint" style={{ margin: 0 }}>
                            +{uploadFiles.length - 5} more files
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                  <div className="field">
                    <label className="label" htmlFor="evidence-metadata">
                      metadata_json
                    </label>
                    <textarea
                      id="evidence-metadata"
                      className="textarea"
                      value={uploadMetadata}
                      onChange={(event) => setUploadMetadata(event.target.value)}
                      disabled={!canUploadEvidence || uploadBusy}
                    />
                  </div>
                  <div className="actions">
                    <button className="button button-primary" type="submit" disabled={!canUploadEvidence || uploadBusy}>
                      {uploadBusy ? 'Uploading...' : uploadFiles.length > 1 ? 'Upload evidence batch' : 'Upload evidence'}
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
                              <td>
                                <strong>{item.name}</strong>
                                {typeof item.metadata_json.relative_path === 'string' && item.metadata_json.relative_path !== item.name && (
                                  <p className="hint">{item.metadata_json.relative_path}</p>
                                )}
                              </td>
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
