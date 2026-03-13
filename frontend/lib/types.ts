export type UserRole =
  | 'org_admin'
  | 'auditor'
  | 'client_viewer'
  | 'security_reviewer'
  | 'remediation_manager';

export type SessionState = {
  token: string;
  refreshToken: string;
  orgId: string;
  email: string;
  role: UserRole | '';
  mfa: boolean;
};

export type Project = {
  id: string;
  org_id: string;
  name: string;
  description: string;
  criticality: 'low' | 'medium' | 'high';
  created_at?: string;
};

export type AuditRun = {
  id: string;
  org_id: string;
  project_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  catalog_version: string;
  progress_json: Record<string, unknown>;
  summary_json: Record<string, unknown>;
  risk_score: number | null;
  risk_level: string | null;
  report_evidence_id: string | null;
  signature_bundle_json?: Record<string, unknown> | null;
  created_at?: string;
  updated_at?: string;
};

export type Finding = {
  id: string;
  org_id: string;
  project_id: string;
  audit_run_id: string;
  control_id: string;
  title: string;
  severity: 'low' | 'medium' | 'high';
  result: 'pass' | 'fail' | 'partial';
  confidence: number;
  notes: string;
  status: 'open' | 'pending_validation' | 'accepted' | 'resolved';
  evidence_refs_json: string[];
};

export type RemediationTask = {
  id: string;
  org_id: string;
  project_id: string;
  audit_run_id: string;
  finding_id: string | null;
  title: string;
  description: string;
  assignee_user_id: string | null;
  due_date: string | null;
  sla_due_at: string | null;
  status: string;
  created_at?: string;
};

export type Integration = {
  id: string;
  org_id: string;
  project_id: string;
  provider: string;
  name: string;
  config_json: Record<string, unknown>;
  secret_ref: string | null;
  is_enabled: boolean;
  created_at?: string;
};

export type EvidenceItem = {
  id: string;
  org_id: string;
  project_id: string;
  audit_run_id: string | null;
  integration_id: string | null;
  item_type: string;
  name: string;
  object_key: string;
  sha256: string;
  metadata_json: Record<string, unknown>;
  scan_status: string | null;
  quarantine_reason: string | null;
  signature_bundle_json: Record<string, unknown> | null;
  created_at?: string;
};

export type FeatureFlags = {
  enterprise_features_enabled: boolean;
  feature_auth_enterprise: boolean;
  feature_scim: boolean;
  feature_secret_store: boolean;
  feature_upload_av_scan: boolean;
  feature_signing: boolean;
  feature_rbac_abac: boolean;
  feature_approvals: boolean;
  feature_reporting_package: boolean;
  feature_pricing: boolean;
};

export type PricingPlan = {
  org_id: string;
  plan_code: string;
  max_assets: number;
  max_upload_bytes: number;
  modules_json: Record<string, boolean>;
};

export type OutboundIntegration = {
  id: string;
  kind: string;
  name: string;
  config_json: Record<string, unknown>;
  secret_ref: string | null;
  is_enabled: boolean;
};

export type DashboardReadinessItem = {
  key: string;
  label: string;
  ready: boolean;
  detail: string;
};

export type DashboardRecentRun = {
  id: string;
  project_id: string;
  project_name: string;
  status: AuditRun['status'];
  risk_score: number | null;
  risk_level: string | null;
  updated_at: string;
};

export type DashboardActivity = {
  id: number;
  action: string;
  entity_type: string;
  entity_id: string;
  created_at: string;
};

export type AuthConfig = {
  mock_login_enabled: boolean;
  enterprise_auth_enabled: boolean;
  demo_org_id: string;
};

export type OrganizationLegalStatus = {
  dpa_status: string;
  dpa_reference: string | null;
  dpa_signed_at: string | null;
  onboarding_status: string;
  onboarding_completed_at: string | null;
};

export type OrganizationDashboard = {
  org_id: string;
  org_name: string;
  generated_at: string;
  legal: OrganizationLegalStatus;
  summary: {
    projects_total: number;
    audit_runs_total: number;
    active_runs: number;
    completed_runs: number;
    evidence_total: number;
    quarantined_evidence: number;
    open_findings: number;
    critical_findings: number;
    overdue_tasks: number;
    project_integrations: number;
    outbound_integrations: number;
    audit_coverage_pct: number;
    automation_coverage_pct: number;
    evidence_hygiene_pct: number;
  };
  plan: {
    plan_code: string;
    max_assets: number;
    assets_used: number;
    asset_usage_pct: number;
    max_upload_bytes: number;
    modules_enabled: string[];
  };
  readiness: {
    score: number;
    items: DashboardReadinessItem[];
  };
  recent_runs: DashboardRecentRun[];
  recent_activity: DashboardActivity[];
};

export type PortfolioProjectEntry = {
  project: Project;
  latest_run: AuditRun | null;
  runs_total: number;
  completed_runs: number;
};

export type PortfolioRunEntry = {
  project: {
    id: string;
    name: string;
  };
  run: AuditRun;
};

export type OrganizationPortfolio = {
  projects: PortfolioProjectEntry[];
  audit_runs: PortfolioRunEntry[];
  reports: PortfolioRunEntry[];
};

export type PaginatedResponse<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};
