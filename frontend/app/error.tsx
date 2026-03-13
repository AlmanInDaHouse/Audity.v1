'use client';

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="login-wrap">
      <div className="card" style={{ maxWidth: 720 }}>
        <h1 className="page-title">Something went wrong</h1>
        <p className="page-subtitle">The UI hit an unexpected state. Refresh the route or retry the last action.</p>
        <p className="error-text">{error.message}</p>
        <div className="actions" style={{ marginTop: 16 }}>
          <button type="button" className="button button-primary" onClick={reset}>
            Retry
          </button>
        </div>
      </div>
    </div>
  );
}
