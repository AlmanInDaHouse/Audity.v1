'use client';

type PaginationProps = {
  page: number;
  pageSize: number;
  total: number;
  onChange: (next: number) => void;
};

export function Pagination({ page, pageSize, total, onChange }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canPrev = page > 1;
  const canNext = page < totalPages;

  return (
    <div className="pagination">
      <p style={{ margin: 0, color: '#5a6f87' }}>
        Page {page} of {totalPages} ({total} items)
      </p>
      <div className="actions">
        <button type="button" className="button button-ghost" onClick={() => onChange(page - 1)} disabled={!canPrev}>
          Previous
        </button>
        <button type="button" className="button button-ghost" onClick={() => onChange(page + 1)} disabled={!canNext}>
          Next
        </button>
      </div>
    </div>
  );
}
