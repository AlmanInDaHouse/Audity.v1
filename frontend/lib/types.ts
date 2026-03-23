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
  frameworks: string[];
  created_at?: string;
};

export type AuditRun = {
  id: string;
  org_id: string;
  project_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  catalog_version_id: string | null;
  catalog_version: string;
  frameworks_json: string[];
  catalog_checksum: string | null;
  progress_json: Record<string, unknown>;
  summary_json: Record<string, unknown>;
  control_posture_score: number | null;
  control_posture_level: string | null;
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

export type SecurityDimensionProfile = {
  id: string;
  org_id: string;
  project_id: string;
  code: string;
  name: string;
  description: string;
  order_index: number;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
};

export type RiskAsset = {
  id: string;
  org_id: string;
  project_id: string;
  name: string;
  asset_type: string;
  owner: string | null;
  description: string;
  criticality: 'low' | 'medium' | 'high';
  metadata_json: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
};

export type RiskAssetRelation = {
  id: string;
  org_id: string;
  project_id: string;
  source_asset_id: string;
  target_asset_id: string;
  relation_type: string;
  description: string;
  created_at?: string;
};

export type RiskThreat = {
  id: string;
  org_id: string;
  project_id: string;
  name: string;
  category: string;
  description: string;
  source: string | null;
  created_at?: string;
  updated_at?: string;
};

export type RiskSafeguard = {
  id: string;
  org_id: string;
  project_id: string;
  name: string;
  safeguard_type: string;
  description: string;
  status: string;
  reference: string | null;
  created_at?: string;
  updated_at?: string;
};

export type RiskAssessment = {
  id: string;
  org_id: string;
  project_id: string;
  name: string;
  methodology: string;
  status: string;
  scope_summary: string;
  notes: string;
  assessed_at: string | null;
  created_by_user_id: string | null;
  created_at?: string;
  updated_at?: string;
};

export type RiskScenario = {
  id: string;
  org_id: string;
  project_id: string;
  assessment_id: string;
  asset_id: string | null;
  threat_id: string | null;
  safeguard_id: string | null;
  title: string;
  description: string;
  likelihood: string | null;
  impact: string | null;
  risk_level: string | null;
  dimension_values_json: Record<string, string>;
  notes: string;
  created_at?: string;
  updated_at?: string;
};

export type RiskTreatmentDecision = {
  id: string;
  org_id: string;
  project_id: string;
  assessment_id: string;
  scenario_id: string;
  safeguard_id: string | null;
  title: string;
  decision: string;
  status: string;
  applies_to: string;
  effectiveness_pct: number;
  rationale: string;
  implementation_notes: string;
  owner_user_id: string | null;
  decided_by_user_id: string | null;
  due_date: string | null;
  review_due_at: string | null;
  metadata_json: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
};

export type RiskScenarioEvaluation = {
  id: string;
  org_id: string;
  project_id: string;
  assessment_id: string;
  scenario_id: string;
  version: number;
  engine_version: string;
  inherent_likelihood: string;
  inherent_impact: string;
  inherent_score: number;
  inherent_level: string;
  residual_likelihood: string;
  residual_impact: string;
  residual_score: number;
  residual_level: string;
  input_snapshot_json: Record<string, unknown>;
  trace_json: Record<string, unknown>;
  notes: string;
  created_by_user_id: string | null;
  created_at?: string;
};

export type RiskRegisterTraceability = {
  evaluation_versions: number;
  treatments_total: number;
  implemented_treatments: number;
  accepted_treatments: number;
  last_evaluated_at: string | null;
};

export type RiskRegisterEntry = {
  scenario: RiskScenario;
  latest_evaluation: RiskScenarioEvaluation | null;
  treatments: RiskTreatmentDecision[];
  traceability: RiskRegisterTraceability;
};

export type RiskOverview = {
  dimensions: SecurityDimensionProfile[];
  assets: RiskAsset[];
  asset_relations: RiskAssetRelation[];
  threats: RiskThreat[];
  safeguards: RiskSafeguard[];
  assessments: RiskAssessment[];
  scenarios: RiskScenario[];
  risk_register: RiskRegisterEntry[];
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
  max_projects: number;
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
  control_posture_score: number | null;
  control_posture_level: string | null;
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
    max_projects: number;
    projects_used: number;
    project_usage_pct: number;
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
