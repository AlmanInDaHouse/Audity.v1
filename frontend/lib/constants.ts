export const PROJECT_FRAMEWORKS = ['ISO27001', 'ENS', 'RGPD'] as const;

export const PROJECT_INTEGRATION_CATALOG = [
  { provider: 'github', label: 'GitHub', description: 'Source repos and policy-as-code evidence.' },
  { provider: 'idp', label: 'IdP', description: 'Identity access and MFA posture.' },
  { provider: 'cloud', label: 'Cloud', description: 'Cloud account posture snapshots.' },
  { provider: 'siem', label: 'SIEM', description: 'Security events and incident traces.' },
  { provider: 'qlik', label: 'Qlik', description: 'Business intelligence controls (placeholder).' },
] as const;

export const OUTBOUND_INTEGRATION_CATALOG = [
  { kind: 'github', label: 'GitHub' },
  { kind: 'idp', label: 'IdP' },
  { kind: 'cloud', label: 'Cloud' },
  { kind: 'siem', label: 'SIEM' },
  { kind: 'qlik', label: 'Qlik' },
] as const;
