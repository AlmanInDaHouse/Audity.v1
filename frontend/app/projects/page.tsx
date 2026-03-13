'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { useEffect } from 'react';

import { Pagination } from '@/components/pagination';
import { StatusBadge } from '@/components/status-badge';
import { useSession } from '@/components/session-context';
import { useToast } from '@/components/toast-provider';
import { hasRole } from '@/lib/auth';
import { apiJson } from '@/lib/api';
import { formatDateTime, formatRisk } from '@/lib/format';
import type { OrganizationPortfolio, PortfolioProjectEntry } from '@/lib/types';

const PAGE_SIZE = 8;

export default function ProjectsPage() {
  const { session } = useSession();
  const { pushToast } = useToast();
  const canCreate = hasRole(session.role, ['org_admin', 'auditor']);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [criticality, setCriticality] = useState<'all' | 'low' | 'medium' | 'high'>('all');
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<PortfolioProjectEntry[]>([]);

  useEffect(() => {
    if (!session.orgId) {
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError('');

    apiJson<OrganizationPortfolio>(`/organizations/${session.orgId}/portfolio`)
      .then((portfolio) => {
        if (!cancelled) {
          setItems(portfolio.projects);
        }
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : 'Failed to load projects';
        if (!cancelled) {
          setError(message);
          pushToast({ tone: 'error', title: 'Error loading projects', message });
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
  }, [session.orgId, pushToast]);

  const filtered = useMemo(() => {
    return items.filter((entry) => {
      const bySearch =
        entry.project.name.toLowerCase().includes(search.toLowerCase()) ||
        entry.project.description.toLowerCase().includes(search.toLowerCase());
      const byCriticality = criticality === 'all' || entry.project.criticality === criticality;
      return bySearch && byCriticality;
    });
  }, [items, search, criticality]);

  const paginated = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filtered.slice(start, start + PAGE_SIZE);
  }, [filtered, page]);

  useEffect(() => {
    setPage(1);
  }, [search, criticality]);

  return (
    <section className="stack">
      <header className="page-header">
        <div>
          <h1 className="page-title">Projects</h1>
          <p className="page-subtitle">Audit-ready portfolio with latest run status and risk.</p>
        </div>
        {canCreate && (
          <Link href="/projects/new" className="button button-primary">
            New Project
          </Link>
        )}
      </header>

      <div className="card">
        <div className="row">
          <div className="field">
            <label htmlFor="search-project" className="label">
              Search
            </label>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <Search size={16} />
              <input
                id="search-project"
                className="input"
                placeholder="Project name or description"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
          </div>
          <div className="field">
            <label htmlFor="criticality-filter" className="label">
              Criticality
            </label>
            <select
              id="criticality-filter"
              className="select"
              value={criticality}
              onChange={(event) => setCriticality(event.target.value as 'all' | 'low' | 'medium' | 'high')}
            >
              <option value="all">All</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        {error && <p className="error-text">{error}</p>}
        {loading && (
          <div className="stack">
            <div className="skeleton" style={{ height: 38 }} />
            <div className="skeleton" style={{ height: 38 }} />
            <div className="skeleton" style={{ height: 38 }} />
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="empty-state">
            <strong>No projects found.</strong>
            <p>{search || criticality !== 'all' ? 'Adjust filters and try again.' : 'Create your first project to start auditing.'}</p>
          </div>
        )}

        {!loading && filtered.length > 0 && (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Criticality</th>
                    <th>Last Audit</th>
                    <th>Risk Score</th>
                    <th>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {paginated.map((entry) => (
                    <tr key={entry.project.id}>
                      <td>
                        <Link href={`/projects/${entry.project.id}`} style={{ color: '#0b6f66', fontWeight: 700 }}>
                          {entry.project.name}
                        </Link>
                        <p className="hint">{entry.project.description || 'No description provided.'}</p>
                      </td>
                      <td>
                        <StatusBadge value={entry.project.criticality} />
                      </td>
                      <td>{entry.latest_run ? <StatusBadge value={entry.latest_run.status} /> : <span className="hint">No runs</span>}</td>
                      <td>{formatRisk(entry.latest_run?.risk_score)}</td>
                      <td>{formatDateTime(entry.latest_run?.updated_at || entry.project.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} total={filtered.length} onChange={setPage} />
          </>
        )}
      </div>
    </section>
  );
}
