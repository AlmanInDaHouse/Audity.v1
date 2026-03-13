'use client';

import type { SessionState, UserRole } from '@/lib/types';

const STORAGE_KEYS = {
  token: 'audity_token',
  refreshToken: 'audity_refresh_token',
  orgId: 'audity_org_id',
  email: 'audity_user_email',
  role: 'audity_user_role',
  mfa: 'audity_user_mfa',
} as const;
const COOKIE_TOKEN_KEY = 'audity_session_token';

const EMPTY_SESSION: SessionState = {
  token: '',
  refreshToken: '',
  orgId: '',
  email: '',
  role: '',
  mfa: false,
};

type TokenPayload = {
  email?: string;
  org_id?: string;
  role?: string;
  mfa?: boolean;
};

function decodePayload(token: string): TokenPayload {
  try {
    const part = token.split('.')[1];
    if (!part) {
      return {};
    }
    const normalized = part.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=');
    const json = atob(padded);
    return JSON.parse(json) as TokenPayload;
  } catch {
    return {};
  }
}

function inferRole(role: string | undefined): UserRole | '' {
  if (
    role === 'org_admin' ||
    role === 'auditor' ||
    role === 'client_viewer' ||
    role === 'security_reviewer' ||
    role === 'remediation_manager'
  ) {
    return role;
  }
  return '';
}

export function getStoredSession(): SessionState {
  if (typeof window === 'undefined') {
    return EMPTY_SESSION;
  }
  const token = localStorage.getItem(STORAGE_KEYS.token) || '';
  const payload = decodePayload(token);
  return {
    token,
    refreshToken: localStorage.getItem(STORAGE_KEYS.refreshToken) || '',
    orgId: localStorage.getItem(STORAGE_KEYS.orgId) || payload.org_id || '',
    email: localStorage.getItem(STORAGE_KEYS.email) || payload.email || '',
    role: inferRole((localStorage.getItem(STORAGE_KEYS.role) || payload.role || '').trim()),
    mfa: (localStorage.getItem(STORAGE_KEYS.mfa) || '') === 'true' || Boolean(payload.mfa),
  };
}

export function saveSession(next: SessionState): void {
  if (typeof window === 'undefined') {
    return;
  }
  localStorage.setItem(STORAGE_KEYS.token, next.token);
  localStorage.setItem(STORAGE_KEYS.refreshToken, next.refreshToken);
  localStorage.setItem(STORAGE_KEYS.orgId, next.orgId);
  localStorage.setItem(STORAGE_KEYS.email, next.email);
  localStorage.setItem(STORAGE_KEYS.role, next.role);
  localStorage.setItem(STORAGE_KEYS.mfa, String(next.mfa));
  document.cookie = `${COOKIE_TOKEN_KEY}=${encodeURIComponent(next.token)}; Path=/; SameSite=Lax`;
}

export function clearSession(): void {
  if (typeof window === 'undefined') {
    return;
  }
  Object.values(STORAGE_KEYS).forEach((key) => localStorage.removeItem(key));
  document.cookie = `${COOKIE_TOKEN_KEY}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export function hasRole(role: SessionState['role'], allowed: UserRole[]): boolean {
  return Boolean(role && allowed.includes(role));
}
