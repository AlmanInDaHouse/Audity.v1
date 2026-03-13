'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { Pagination } from '@/components/pagination';
import { useSession } from '@/components/session-context';
import { apiDownload, apiJson } from '@/lib/api';
import { formatDateTime, formatRisk } from '@/lib/format';
import type { OrganizationPortfolio, PortfolioRunEntry } from '@/lib/types';

const PAGE_SIZE = 10;

export default function ReportsPage() {
  const { session } = useSession();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [rows, setRows] = useState<PortfolioRunEntry[]>([]);
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!session.orgId) {
      return;
    }
    setLoading(true);
    setError('');
    apiJson<OrganizationPortfolio>(`/organizations/${session.orgId}/portfolio`)
      .then((portfolio) => {
        setRows(
          [...portfolio.reports].sort(
            (a, b) => new Date(b.run.updated_at || '').valueOf() - new Date(a.run.updated_at || '').valueOf(),
          ),
        );
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load reports'))
      .finally(() => setLoading(false));
  }, [session.orgId]);

  const paginated = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return rows.slice(start, start + PAGE_SIZE);
  }, [rows, page]);

  return (
    <section className="stack">
      <header className="page-header">
        <div>
          <h1 className="page-title">Reports</h1>
          <p className="page-subtitle">Completed run reports and exports.</p>
        </div>
      </header>

      <article className="card">
        {error && <p className="error-text">{error}</p>}
        {loading && <div className="skeleton" style={{ height: 120 }} />}
        {!loading && rows.length === 0 && (
          <div className="empty-state">
            <strong>No reports available yet.</strong>
            <p>Complete an audit run to generate a PDF report.</p>
          </div>
        )}
        {!loading && rows.length > 0 && (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Project</th>
                    <th>Run</th>
                    <th>Risk</th>
                    <th>Generated</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginated.map((row) => (
                    <tr key={row.run.id}>
                      <td>{row.project.name}</td>
                      <td>{row.run.id.slice(0, 10)}</td>
                      <td>{formatRisk(row.run.risk_score)}</td>
                      <td>{formatDateTime(row.run.updated_at)}</td>
                      <td>
                        <button
                          type="button"
                          className="button button-secondary"
                          onClick={() =>
                            row.run.report_evidence_id &&
                            apiDownload(`/evidence/${row.run.report_evidence_id}/download`, `audit-report-${row.run.id}.pdf`)
                          }
                        >
                          Download PDF
                        </button>
                        <Link href={`/projects/${row.project.id}/runs/${row.run.id}`} className="button button-ghost">
                          Open run
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} total={rows.length} onChange={setPage} />
          </>
        )}
      </article>
    </section>
  );
}
