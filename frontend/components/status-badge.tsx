type BadgeKind = 'low' | 'medium' | 'high' | 'queued' | 'running' | 'completed' | 'failed' | 'clean' | 'quarantined';

const MAP: Record<BadgeKind, string> = {
  low: 'badge-low',
  medium: 'badge-medium',
  high: 'badge-high',
  queued: 'badge-queued',
  running: 'badge-running',
  completed: 'badge-completed',
  failed: 'badge-failed',
  clean: 'badge-clean',
  quarantined: 'badge-quarantined',
};

export function StatusBadge({ value }: { value: string }) {
  const normalized = value.toLowerCase();
  const kind: BadgeKind =
    normalized === 'low' ||
    normalized === 'medium' ||
    normalized === 'high' ||
    normalized === 'queued' ||
    normalized === 'running' ||
    normalized === 'completed' ||
    normalized === 'failed' ||
    normalized === 'clean' ||
    normalized === 'quarantined'
      ? normalized
      : 'medium';
  return <span className={`badge ${MAP[kind]}`}>{value}</span>;
}
