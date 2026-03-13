'use client';

import { useEffect, useMemo, useState } from 'react';

import { Pagination } from '@/components/pagination';
import { useSession } from '@/components/session-context';
import { StatusBadge } from '@/components/status-badge';
import { apiDownload, apiJson } from '@/lib/api';
import { formatDateTime } from '@/lib/format';
import type { EvidenceItem, FeatureFlags, PaginatedResponse, Project } from '@/lib/types';

const PAGE_SIZE = 12;

export default function EvidenceLibraryPage() {
  const { session } = useSession();
  const [projects, setProjects] = useState<Project[]>([]);
  const [features, setFeatures] = useState<FeatureFlags | null>(null);
  const [items, setItems] = useState<PaginatedResponse<EvidenceItem>>({ items: [], page: 1, page_size: PAGE_SIZE, total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [projectFilter, setProjectFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [scanFilter, setScanFilter] = useState('all');
  const [verifyMessage, setVerifyMessage] = useState('');

  const knownTypes = useMemo(() => {
    const set = new Set<string>();
    items.items.forEach((item) => set.add(item.item_type));
    return [...set];
  }, [items.items]);

  async function load(currentPage: number) {
    const query = new URLSearchParams();
    query.set('page', String(currentPage));
    query.set('page_size', String(PAGE_SIZE));
    if (projectFilter !== 'all') {
      query.set('project_id', projectFilter);
    }
    if (typeFilter !== 'all') {
      query.set('item_type', typeFilter);
    }
    if (scanFilter !== 'all') {
      query.set('scan_status', scanFilter);
    }
    const payload = await apiJson<PaginatedResponse<EvidenceItem>>(`/organizations/${session.orgId}/evidence?${query.toString()}`);
    setItems(payload);
  }

  useEffect(() => {
    if (!session.orgId) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    Promise.all([
      apiJson<Project[]>(`/organizations/${session.orgId}/projects`),
      apiJson<FeatureFlags>('/enterprise/features'),
      load(page),
    ])
      .then(([projectsPayload, featurePayload]) => {
        if (!cancelled) {
          setProjects(projectsPayload);
          setFeatures(featurePayload);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load evidence');
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
  }, [session.orgId, page, projectFilter, typeFilter, scanFilter]);

  async function verifySignature(evidenceId: string) {
    try {
      const payload = await apiJson<{ valid: boolean }>(`/evidence/${evidenceId}/verify-signature`);
      setVerifyMessage(payload.valid ? 'Signature valid.' : 'Signature invalid.');
    } catch (err) {
      setVerifyMessage(err instanceof Error ? err.message : 'Verification failed');
    }
  }

  return (
    <section className="stack">
      <header className="page-header">
        <div>
          <h1 className="page-title">Evidence Library</h1>
          <p className="page-subtitle">Global evidence view across projects.</p>
        </div>
      </header>

      <article className="card">
        <div className="row">
          <div className="field">
            <label className="label" htmlFor="project-filter">
              Project
            </label>
            <select id="project-filter" className="select" value={projectFilter} onChange={(event) => setProjectFilter(event.target.value)}>
              <option value="all">All projects</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="label" htmlFor="type-filter">
              Type
            </label>
            <select id="type-filter" className="select" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
              <option value="all">All types</option>
              {knownTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="label" htmlFor="scan-filter">
              Scan state
            </label>
            <select id="scan-filter" className="select" value={scanFilter} onChange={(event) => setScanFilter(event.target.value)}>
              <option value="all">All</option>
              <option value="clean">Clean</option>
              <option value="infected">Infected</option>
              <option value="scan_error">Scan error</option>
            </select>
          </div>
        </div>
      </article>

      <article className="card">
        {error && <p className="error-text">{error}</p>}
        {loading && (
          <div className="stack">
            <div className="skeleton" style={{ height: 44 }} />
            <div className="skeleton" style={{ height: 44 }} />
          </div>
        )}
        {!loading && items.items.length === 0 && (
          <div className="empty-state">
            <strong>No evidence found.</strong>
          </div>
        )}
        {!loading && items.items.length > 0 && (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Project</th>
                    <th>Type</th>
                    <th>Scan</th>
                    <th>Metadata</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.items.map((item) => (
                    <tr key={item.id}>
                      <td>{item.name}</td>
                      <td>{projects.find((project) => project.id === item.project_id)?.name || item.project_id}</td>
                      <td>{item.item_type}</td>
                      <td>
                        <StatusBadge value={item.scan_status === 'clean' ? 'clean' : 'quarantined'} />
                      </td>
                      <td>
                        <details>
                          <summary>View</summary>
                          <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(item.metadata_json, null, 2)}</pre>
                        </details>
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
                          disabled={!features?.feature_signing}
                          title={!features?.feature_signing ? 'feature_signing disabled' : 'Verify signature'}
                          onClick={() => verifySignature(item.id)}
                        >
                          Verify signature
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={items.page} pageSize={items.page_size} total={items.total} onChange={setPage} />
          </>
        )}
        {verifyMessage && <p className="success-text">{verifyMessage}</p>}
      </article>
    </section>
  );
}
