// Shared reusable UI components
import React, { useCallback, useState } from 'react';
import type { Severity } from '../types';
import { severityBadgeClass, severityColor, qualityScoreColor } from '../utils/helpers';

// ── LoadingSpinner ───────────────────────────────────────────────────────────
export function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const cls = size === 'lg' ? 'spinner spinner-lg' : 'spinner';
  return <div className={cls} aria-label="Loading" />;
}

// ── EmptyState ───────────────────────────────────────────────────────────────
export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">
        {icon || (
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.6 }}>
            <rect x="2" y="4" width="20" height="16" rx="2" />
            <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
          </svg>
        )}
      </div>
      <div className="empty-state-title">{title}</div>
      {description && <p className="empty-state-desc">{description}</p>}
      {action}
    </div>
  );
}

// ── ErrorAlert ───────────────────────────────────────────────────────────────
export function ErrorAlert({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="alert alert-danger" role="alert">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>Error</div>
        {message}
        {onRetry && (
          <button className="btn btn-secondary btn-sm" style={{ marginTop: 10 }} onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

// ── OfflineAlert ─────────────────────────────────────────────────────────────
export function OfflineAlert({ onRetry }: { onRetry?: () => void }) {
  return (
    <div className="alert alert-warning" role="alert">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
        <line x1="1" y1="1" x2="23" y2="23" />
        <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55" />
        <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39" />
        <path d="M10.71 5.05A16 16 0 0 1 22.58 9" />
        <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88" />
        <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
        <line x1="12" y1="20" x2="12.01" y2="20" />
      </svg>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>Backend Unavailable</div>
        The ECO-SHIELD API server is not reachable. Make sure it is running on{' '}
        <code style={{ fontSize: 12 }}>http://localhost:8000</code>.
        {onRetry && (
          <button className="btn btn-secondary btn-sm" style={{ marginTop: 10 }} onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

// ── SeverityBadge ────────────────────────────────────────────────────────────
export function SeverityBadge({ severity }: { severity: Severity | string }) {
  return (
    <span className={severityBadgeClass(severity)}>
      {severity}
    </span>
  );
}

// ── QualityScoreRing ──────────────────────────────────────────────────────────
export function QualityScoreRing({
  score,
  size = 80,
}: {
  score: number;
  size?: number;
}) {
  const color = qualityScoreColor(score);
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const fill = clamp((score / 100) * circ, 0, circ);
  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth={7} />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth={7}
          strokeDasharray={`${fill} ${circ - fill}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dasharray 0.5s ease' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ fontSize: size * 0.22, fontWeight: 700, color }}>{Math.round(score)}</span>
      </div>
    </div>
  );
}

function clamp(n: number, min: number, max: number) { return Math.min(max, Math.max(min, n)); }

// ── SourceChip ────────────────────────────────────────────────────────────────
export function SourceChip({ source }: { source: string }) {
  const labels: Record<string, string> = { demo: 'Synthetic', upload: 'Upload', live: 'Live' };
  return <span className={`source-chip ${source}`}>{labels[source] || source}</span>;
}

// ── DataSourceBanner ──────────────────────────────────────────────────────────
export function DataSourceBanner({ source }: { source: string }) {
  if (source === 'demo') {
    return (
      <div className="alert alert-info" style={{ marginBottom: 16 }}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        <span><strong>Synthetic Dataset</strong> — This dataset was generated for testing. Telemetry values demonstrate algorithm behavior.</span>
      </div>
    );
  }
  return null;
}

// ── UploadZone ────────────────────────────────────────────────────────────────
export function UploadZone({
  onFile,
  accept = '.csv',
  loading = false,
}: {
  onFile: (f: File) => void;
  accept?: string;
  loading?: boolean;
}) {
  const [drag, setDrag] = useState(false);

  const handleFile = useCallback((f: File) => { onFile(f); }, [onFile]);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  };

  return (
    <label
      className={`upload-zone ${drag ? 'drag-over' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragEnter={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={onDrop}
    >
      <input
        type="file"
        accept={accept}
        style={{ display: 'none' }}
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        disabled={loading}
      />
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <LoadingSpinner size="lg" />
          <div className="text-secondary">Uploading and validating…</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 52,
            height: 52,
            borderRadius: '50%',
            background: 'var(--blue-50)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 2,
          }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="var(--blue-600)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--text-primary)' }}>
            Drag and drop your telemetry CSV file here
          </div>
          <div className="text-sm text-tertiary">
            Supports solar telemetry up to 50 MB
          </div>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            background: 'var(--blue-600)',
            color: '#ffffff',
            padding: '8px 20px',
            borderRadius: 'var(--radius-sm)',
            fontWeight: 600,
            fontSize: 13,
            boxShadow: '0 2px 6px rgba(37,99,235,0.25)',
            marginTop: 4,
          }}>
            Browse Files
          </div>
        </div>
      )}
    </label>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: string; label: string }[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="tabs">
      {tabs.map((t) => (
        <button
          key={t.id}
          className={`tab-btn ${active === t.id ? 'active' : ''}`}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

// ── InfoRow ───────────────────────────────────────────────────────────────────
export function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid var(--border-light)', gap: 12 }}>
      <span style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500 }}>{label}</span>
      <span style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 500, textAlign: 'right' }}>{value ?? '—'}</span>
    </div>
  );
}

// ── PageHeader ────────────────────────────────────────────────────────────────
export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
      <div>
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {actions && <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>{actions}</div>}
    </div>
  );
}

// ── Skeleton card ─────────────────────────────────────────────────────────────
export function SkeletonCard() {
  return (
    <div className="card" style={{ padding: 20 }}>
      <div className="skeleton" style={{ height: 16, width: '40%', marginBottom: 12 }} />
      <div className="skeleton" style={{ height: 40, width: '70%', marginBottom: 8 }} />
      <div className="skeleton" style={{ height: 12, width: '55%' }} />
    </div>
  );
}

// ── Pagination ────────────────────────────────────────────────────────────────
export function Pagination({
  page,
  pageSize,
  total,
  onChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onChange: (p: number) => void;
}) {
  const totalPages = Math.ceil(total / pageSize);
  if (totalPages <= 1) return null;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end', padding: '12px 0' }}>
      <span className="text-sm text-secondary">
        {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}
      </span>
      <button className="btn btn-secondary btn-sm" onClick={() => onChange(page - 1)} disabled={page <= 1}>
        ←
      </button>
      <button className="btn btn-secondary btn-sm" onClick={() => onChange(page + 1)} disabled={page >= totalPages}>
        →
      </button>
    </div>
  );
}
