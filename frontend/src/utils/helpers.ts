// Shared utility functions
import type { Severity } from '../types';

export function formatNumber(n: number | null | undefined, decimals = 1): string {
  if (n === null || n === undefined || isNaN(n)) return '—';
  return n.toFixed(decimals);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch { return '—'; }
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export function severityColor(sev: Severity | string): string {
  switch (sev) {
    case 'critical': return 'var(--rose-600)';
    case 'high':     return 'var(--orange-500)';
    case 'medium':   return 'var(--amber-600)';
    case 'low':      return 'var(--sky-500)';
    default:         return 'var(--slate-500)';
  }
}

export function severityBadgeClass(sev: Severity | string): string {
  switch (sev) {
    case 'critical': return 'badge badge-danger';
    case 'high':     return 'badge badge-warning';
    case 'medium':   return 'badge badge-warning';
    case 'low':      return 'badge badge-info';
    default:         return 'badge badge-neutral';
  }
}

export function qualityScoreColor(score: number): string {
  if (score >= 80) return 'var(--emerald-500)';
  if (score >= 60) return 'var(--amber-500)';
  if (score >= 40) return 'var(--orange-500)';
  return 'var(--rose-500)';
}

export function priorityColor(priority: string): string {
  switch (priority.toLowerCase()) {
    case 'high':   return 'var(--rose-500)';
    case 'medium': return 'var(--amber-500)';
    default:       return 'var(--emerald-500)';
  }
}

export function clamp(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, n));
}

export function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '…' : s;
}

export function downloadJson(data: unknown, filename: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

export function downloadCsvString(csv: string, filename: string): void {
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}
