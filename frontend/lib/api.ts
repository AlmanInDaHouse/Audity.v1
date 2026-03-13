'use client';

import { clearSession, getStoredSession } from '@/lib/auth';

function resolveApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    if (window.location.protocol === 'https:') {
      return '/api';
    }
    return `${window.location.protocol}//${window.location.hostname}:58000`;
  }
  return process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
}

const API_BASE_URL = resolveApiBaseUrl();

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function readError(response: Response): Promise<string> {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail || `HTTP ${response.status}`;
  }
  const text = await response.text();
  return text || `HTTP ${response.status}`;
}

export async function apiFetch(path: string, init: RequestInit = {}, requireAuth = true): Promise<Response> {
  const headers = new Headers(init.headers || {});
  const body = init.body;
  const hasBody = body !== undefined && body !== null;
  const isFormBody = typeof FormData !== 'undefined' && body instanceof FormData;
  if (hasBody && !isFormBody && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (requireAuth) {
    const session = getStoredSession();
    if (session.token) {
      headers.set('Authorization', `Bearer ${session.token}`);
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    if (requireAuth && response.status === 401 && typeof window !== 'undefined') {
      clearSession();
      window.location.href = '/login';
    }
    throw new ApiError(await readError(response), response.status);
  }

  return response;
}

export async function apiJson<T>(path: string, init?: RequestInit, requireAuth = true): Promise<T> {
  const response = await apiFetch(path, init, requireAuth);
  return (await response.json()) as T;
}

export async function apiDownload(path: string, filename: string): Promise<void> {
  const response = await apiFetch(path);
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export { API_BASE_URL };
