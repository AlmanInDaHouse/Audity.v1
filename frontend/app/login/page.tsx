'use client';

import { useRouter } from 'next/navigation';
import { FormEvent, useEffect, useMemo, useState } from 'react';

import { useSession } from '@/components/session-context';
import { useToast } from '@/components/toast-provider';
import { apiJson } from '@/lib/api';
import type { AuthConfig, SessionState, UserRole } from '@/lib/types';

type DemoUser = {
  email: string;
  role: UserRole;
  label: string;
};

const DEMO_USERS: DemoUser[] = [
  { email: 'admin@demo.local', role: 'org_admin', label: 'Org Admin' },
  { email: 'auditor@demo.local', role: 'auditor', label: 'Security Auditor' },
  { email: 'viewer@demo.local', role: 'client_viewer', label: 'Client Viewer' },
];

type LoginResponse = {
  access_token: string;
  refresh_token?: string;
};

export default function LoginPage() {
  const router = useRouter();
  const { session, setSession, ready } = useSession();
  const { pushToast } = useToast();

  const [orgId, setOrgId] = useState('');
  const [userEmail, setUserEmail] = useState(DEMO_USERS[1].email);
  const [mfa, setMfa] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null);

  useEffect(() => {
    apiJson<AuthConfig>('/auth/config', undefined, false)
      .then((data) => {
        setAuthConfig(data);
        setOrgId(data.demo_org_id || '');
      })
      .catch(() => setAuthConfig({ mock_login_enabled: false, enterprise_auth_enabled: false, demo_org_id: '' }));
  }, []);

  useEffect(() => {
    if (ready && session.token) {
      router.replace('/overview');
    }
  }, [ready, session.token, router]);

  const selectedUser = useMemo(() => DEMO_USERS.find((item) => item.email === userEmail) || DEMO_USERS[0], [userEmail]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      if (!authConfig?.mock_login_enabled) {
        throw new Error('Demo access is disabled in this environment.');
      }
      const payload = await apiJson<LoginResponse>(
        '/auth/mock/login',
        {
          method: 'POST',
          body: JSON.stringify({ email: userEmail, org_id: orgId, mfa }),
        },
        false,
      );

      const nextSession: SessionState = {
        token: payload.access_token,
        refreshToken: payload.refresh_token || '',
        orgId,
        email: userEmail,
        role: selectedUser.role,
        mfa,
      };
      setSession(nextSession);
      pushToast({ tone: 'success', title: 'Logged in', message: `${selectedUser.label} session ready.` });
      router.push('/overview');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
      pushToast({ tone: 'error', title: 'Login failed', message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="card login-card">
        <h1 className="page-title">Audity Access</h1>
        <p className="page-subtitle">
          {authConfig?.mock_login_enabled
            ? 'Use a controlled demo account to enter the workspace.'
            : 'This environment requires enterprise authentication or controlled access.'}
        </p>
        {authConfig?.enterprise_auth_enabled && !authConfig?.mock_login_enabled && (
          <div className="card" style={{ background: '#f8f4e6', borderColor: '#ecd9a2', marginTop: 12 }}>
            <strong>Enterprise authentication is enabled.</strong>
            <p style={{ marginBottom: 0 }}>Mock login is blocked outside controlled demo environments.</p>
          </div>
        )}

        {authConfig?.mock_login_enabled ? (
          <form className="stack" onSubmit={onSubmit} style={{ marginTop: 14 }}>
            <div className="field">
              <label htmlFor="demo-user" className="label">
                Demo user
              </label>
              <select
                id="demo-user"
                className="select"
                value={userEmail}
                onChange={(event) => setUserEmail(event.target.value)}
                aria-label="Select demo user"
                data-testid="login-demo-user"
              >
                {DEMO_USERS.map((user) => (
                  <option key={user.email} value={user.email}>
                    {user.label} ({user.email})
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label htmlFor="demo-org-id" className="label">
                Demo organization
              </label>
              <input
                id="demo-org-id"
                className="input"
                value={orgId}
                onChange={(event) => setOrgId(event.target.value)}
                placeholder="Organization ID"
              />
            </div>

            <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input checked={mfa} onChange={(event) => setMfa(event.target.checked)} type="checkbox" />
              Include MFA claim for sensitive actions
            </label>

            <div className="actions">
              <button className="button button-primary" disabled={loading || !orgId} type="submit" data-testid="login-submit">
                {loading ? 'Signing in...' : 'Login'}
              </button>
            </div>
          </form>
        ) : (
          <div className="card" style={{ marginTop: 14, background: '#f7f7f2' }}>
            <strong>Controlled access required</strong>
            <p style={{ marginBottom: 0 }}>
              Provision enterprise SSO before market-facing onboarding. This pre-GA build disables demo credentials here.
            </p>
          </div>
        )}

        {error && <p className="error-text" style={{ marginTop: 10 }}>{error}</p>}
      </div>
    </div>
  );
}
