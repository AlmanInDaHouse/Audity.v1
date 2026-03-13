export function formatDateTime(value?: string | null): string {
  if (!value) {
    return '-';
  }
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) {
    return '-';
  }
  return date.toLocaleString();
}

export function formatRisk(value?: number | null): string {
  if (value === null || value === undefined) {
    return '-';
  }
  return value.toFixed(1);
}

export function formatPercent(value?: number | null): string {
  if (value === null || value === undefined) {
    return '-';
  }
  return `${Math.round(value)}%`;
}

export function compactId(value: string): string {
  if (value.length < 14) {
    return value;
  }
  return `${value.slice(0, 6)}...${value.slice(-4)}`;
}

export function prettyRole(role: string): string {
  return role.replace(/_/g, ' ');
}
