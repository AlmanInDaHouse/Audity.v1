'use client';

import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { Breadcrumbs } from '@/components/breadcrumbs';
import { useSession } from '@/components/session-context';
import { useToast } from '@/components/toast-provider';
import { hasRole } from '@/lib/auth';
import { apiJson } from '@/lib/api';
import { PROJECT_FRAMEWORKS } from '@/lib/constants';
import type { Project } from '@/lib/types';

type Step = 1 | 2;

export default function NewProjectPage() {
  const router = useRouter();
  const { session } = useSession();
  const { pushToast } = useToast();
  const canCreate = hasRole(session.role, ['org_admin', 'auditor']);

  const [step, setStep] = useState<Step>(1);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [criticality, setCriticality] = useState<'low' | 'medium' | 'high'>('medium');
  const [frameworks, setFrameworks] = useState<string[]>(['ISO27001']);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  if (!canCreate) {
    return (
      <section className="stack">
        <Breadcrumbs items={[{ label: 'Projects', href: '/projects' }, { label: 'New Project' }]} />
        <div className="card">
          <h1 className="page-title">New Project</h1>
          <p className="error-text">Your role cannot create projects.</p>
        </div>
      </section>
    );
  }

  function toggleFramework(framework: string) {
    setFrameworks((current) =>
      current.includes(framework) ? current.filter((item) => item !== framework) : [...current, framework],
    );
  }

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');

    try {
      const payload = await apiJson<Project>(`/organizations/${session.orgId}/projects`, {
        method: 'POST',
        body: JSON.stringify({ name, description, criticality, frameworks }),
      });
      pushToast({
        tone: 'success',
        title: 'Project created',
        message: `${payload.name} initialized with ${frameworks.join(', ')} frameworks.`,
      });
      router.push(`/projects/${payload.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not create project';
      setError(message);
      pushToast({ tone: 'error', title: 'Project creation failed', message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="stack">
      <Breadcrumbs items={[{ label: 'Projects', href: '/projects' }, { label: 'New Project' }]} />
      <header className="page-header">
        <div>
          <h1 className="page-title">Create Project</h1>
          <p className="page-subtitle">Wizard with audit scope setup.</p>
        </div>
      </header>

      <div className="tabs" role="tablist" aria-label="Creation steps">
        <button type="button" className={`tab ${step === 1 ? 'active' : ''}`} onClick={() => setStep(1)}>
          1. Project details
        </button>
        <button type="button" className={`tab ${step === 2 ? 'active' : ''}`} onClick={() => setStep(2)}>
          2. Frameworks
        </button>
      </div>

      <form className="card stack" onSubmit={createProject}>
        {step === 1 && (
          <>
            <div className="field">
              <label htmlFor="project-name" className="label">
                Project name
              </label>
              <input
                id="project-name"
                className="input"
                required
                minLength={2}
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="project-description" className="label">
                Description
              </label>
              <textarea
                id="project-description"
                className="textarea"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="project-criticality" className="label">
                Criticality
              </label>
              <select
                id="project-criticality"
                className="select"
                value={criticality}
                onChange={(event) => setCriticality(event.target.value as 'low' | 'medium' | 'high')}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
          </>
        )}

        {step === 2 && (
          <div className="stack">
            <p className="hint">Framework selection for audit scope. Persisted at project level and frozen in each run.</p>
            {PROJECT_FRAMEWORKS.map((framework) => (
              <label key={framework} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input
                  type="checkbox"
                  checked={frameworks.includes(framework)}
                  onChange={() => toggleFramework(framework)}
                  aria-label={`Enable ${framework}`}
                />
                {framework}
              </label>
            ))}
          </div>
        )}

        <div className="actions">
          {step === 2 && (
            <button type="button" className="button button-ghost" onClick={() => setStep(1)}>
              Back
            </button>
          )}
          {step === 1 && (
            <button type="button" className="button button-ghost" onClick={() => setStep(2)} disabled={!name.trim()}>
              Continue
            </button>
          )}
          {step === 2 && (
            <button type="submit" className="button button-primary" disabled={busy || frameworks.length === 0}>
              {busy ? 'Creating...' : 'Create project'}
            </button>
          )}
        </div>
        {error && <p className="error-text">{error}</p>}
      </form>
    </section>
  );
}
