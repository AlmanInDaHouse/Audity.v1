'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { Pagination } from '@/components/pagination';
import { useSession } from '@/components/session-context';
import { StatusBadge } from '@/components/status-badge';
import { apiJson } from '@/lib/api';
import { formatDateTime, formatRisk } from '@/lib/format';
import type { OrganizationPortfolio, PortfolioRunEntry } from '@/lib/types';

const PAGE_SIZE = 12;

export default function AuditRunsPage() {
  const { session } = useSession();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [items, setItems] = useState<PortfolioRunEntry[]>([]);
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!session.orgId) {
      return;
    }
    setLoading(true);
    setError('');
    apiJson<OrganizationPortfolio>(`/organizations/${session.orgId}/portfolio`)
      .then((portfolio) => {
        setItems(
          [...portfolio.audit_runs].sort(
            (a, b) => new Date(b.run.updated_at || '').valueOf() - new Date(a.run.updated_at || '').valueOf(),
          ),
        );
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load runs');
      })
      .finally(() => setLoading(false));
  }, [session.orgId]);

  const paginated = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return items.slice(start, start + PAGE_SIZE);
  }, [items, page]);

  return (
    <section className="stack">
      <header className="page-header">
        <div>
          <h1 className="page-title">Audit Runs</h1>
          <p className="page-subtitle">Cross-project run tracking.</p>
        </div>
      </header>

      <article className="card">
        {error && <p className="error-text">{error}</p>}
        {loading && (
          <div className="stack">
            <div className="skeleton" style={{ height: 40 }} />
            <div className="skeleton" style={{ height: 40 }} />
          </div>
        )}
        {!loading && items.length === 0 && (
          <div className="empty-state">
            <strong>No runs yet.</strong>
            <p>Create your first run from a project page.</p>
          </div>
        )}
        {!loading && items.length > 0 && (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Project</th>
                    <th>Status</th>
                    <th>Control posture score</th>
                    <th>Updated</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginated.map((item) => (
                    <tr key={item.run.id}>
                      <td>{item.project.name}</td>
                      <td><StatusBadge value={item.run.status} /></td>
                      <td>{formatRisk(item.run.control_posture_score ?? item.run.risk_score)}</td>
                      <td>{formatDateTime(item.run.updated_at)}</td>
                      <td>
                        <Link href={`/projects/${item.project.id}/runs/${item.run.id}`} className="button button-ghost">
                          Open run
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} total={items.length} onChange={setPage} />
          </>
        )}
      </article>
    </section>
  );
}
