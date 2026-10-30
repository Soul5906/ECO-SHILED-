// Anomalies page — sortable, filterable anomaly table
import React, { useState, useMemo } from 'react';
import { useAnalysis } from '../context/AnalysisContext';
import { EmptyState, PageHeader, SeverityBadge, Pagination, DataSourceBanner } from '../components/Shared';
import { AnomalyBarChart } from '../components/Charts';
import { formatDate, formatNumber, downloadCsvString } from '../utils/helpers';
import type { AnomalyRecord, Severity } from '../types';

const PAGE_SIZE = 25;
const SEVERITY_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };

export default function Anomalies() {
  const { currentAnalysis } = useAnalysis();
  const [search, setSearch] = useState('');
  const [sevFilter, setSevFilter] = useState('all');
  const [detFilter, setDetFilter] = useState('all');
  const [sortKey, setSortKey] = useState<'severity' | 'detector' | 'column' | 'timestamp'>('severity');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const anomalies = currentAnalysis?.anomaly_summary?.anomalies ?? [];
  const summary = currentAnalysis?.anomaly_summary;

  const detectors = useMemo(() => Array.from(new Set(anomalies.map((a) => a.detector_name))), [anomalies]);

  const filtered = useMemo(() => {
    let r = anomalies;
    if (sevFilter !== 'all') r = r.filter((a) => a.severity === sevFilter);
    if (detFilter !== 'all') r = r.filter((a) => a.detector_name === detFilter);
    if (search) {
      const q = search.toLowerCase();
      r = r.filter((a) => a.explanation.toLowerCase().includes(q) || (a.column ?? '').toLowerCase().includes(q));
    }
    r = [...r].sort((a, b) => {
      let cmp = 0;
      if (sortKey === 'severity') cmp = (SEVERITY_ORDER[a.severity] ?? 5) - (SEVERITY_ORDER[b.severity] ?? 5);
      else if (sortKey === 'detector') cmp = a.detector_name.localeCompare(b.detector_name);
      else if (sortKey === 'column') cmp = (a.column ?? '').localeCompare(b.column ?? '');
      else if (sortKey === 'timestamp') cmp = (a.timestamp ?? '').localeCompare(b.timestamp ?? '');
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return r;
  }, [anomalies, sevFilter, detFilter, search, sortKey, sortDir]);

  const pageData = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleSort = (k: typeof sortKey) => {
    if (sortKey === k) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortKey(k); setSortDir('asc'); }
    setPage(1);
  };

  const exportCsv = () => {
    const header = 'anomaly_id,detector_name,detector_type,column,timestamp,row_index,measured_value,threshold_used,severity,explanation';
    const rows = filtered.map((a) =>
      [a.anomaly_id, a.detector_name, a.detector_type, a.column ?? '', a.timestamp ?? '', a.row_index ?? '', a.measured_value ?? '', a.threshold_used ?? '', a.severity, `"${a.explanation.replace(/"/g, '""')}"`].join(',')
    );
    downloadCsvString([header, ...rows].join('\n'), 'ecoshield_anomalies.csv');
  };

  if (!currentAnalysis) {
    return (
      <div>
        <PageHeader title="Anomaly Detection" subtitle="Run an analysis first to see detected anomalies." />
        <EmptyState title="No analysis loaded" description="Load a demo scenario or upload a CSV file." />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Anomaly Detection"
        subtitle={`${anomalies.length} anomalies detected · ${summary?.detectors_run?.length ?? 0} detectors run`}
        actions={
          <button className="btn btn-secondary btn-sm" onClick={exportCsv} disabled={filtered.length === 0}>
            Export CSV
          </button>
        }
      />

      <DataSourceBanner source={currentAnalysis.source} />

      {/* Summary chart */}
      {summary && Object.keys(summary.by_severity).length > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header"><span className="card-title">By Severity</span></div>
          <div className="card-body">
            <AnomalyBarChart bySeverity={summary.by_severity} />
          </div>
        </div>
      )}

      {/* Detector summary chips */}
      {summary && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
          {Object.entries(summary.by_detector).map(([det, count]) => (
            <span key={det} className="badge badge-neutral">{det}: {count}</span>
          ))}
        </div>
      )}

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
        <input
          className="input"
          style={{ maxWidth: 260 }}
          placeholder="Search explanations…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
        <select
          className="input select"
          style={{ maxWidth: 160 }}
          value={sevFilter}
          onChange={(e) => { setSevFilter(e.target.value); setPage(1); }}
        >
          <option value="all">All severities</option>
          {['critical', 'high', 'medium', 'low', 'info'].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          className="input select"
          style={{ maxWidth: 200 }}
          value={detFilter}
          onChange={(e) => { setDetFilter(e.target.value); setPage(1); }}
        >
          <option value="all">All detectors</option>
          {detectors.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <span className="text-sm text-secondary" style={{ lineHeight: '36px' }}>{filtered.length} results</span>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <EmptyState icon="✅" title="No anomalies match" description="Adjust filters or run a different scenario." />
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th onClick={() => handleSort('severity')} style={{ cursor: 'pointer' }}>Severity {sortKey === 'severity' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</th>
                  <th onClick={() => handleSort('detector')} style={{ cursor: 'pointer' }}>Detector {sortKey === 'detector' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</th>
                  <th onClick={() => handleSort('column')} style={{ cursor: 'pointer' }}>Column {sortKey === 'column' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</th>
                  <th onClick={() => handleSort('timestamp')} style={{ cursor: 'pointer' }}>Timestamp {sortKey === 'timestamp' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</th>
                  <th>Value</th>
                  <th>Explanation</th>
                </tr>
              </thead>
              <tbody>
                {pageData.map((a) => (
                  <React.Fragment key={a.anomaly_id}>
                    <tr
                      style={{ cursor: 'pointer' }}
                      onClick={() => setExpandedId(expandedId === a.anomaly_id ? null : a.anomaly_id)}
                    >
                      <td><SeverityBadge severity={a.severity} /></td>
                      <td><span className="badge badge-neutral" style={{ fontSize: 11 }}>{a.detector_name}</span></td>
                      <td className="td-mono">{a.column ?? '—'}</td>
                      <td className="text-sm">{a.timestamp ? formatDate(a.timestamp) : `row ${a.row_index ?? '—'}`}</td>
                      <td className="td-mono">{a.measured_value !== undefined && a.measured_value !== null ? formatNumber(a.measured_value, 3) : '—'}</td>
                      <td className="text-sm" style={{ maxWidth: 320 }}>{a.explanation}</td>
                    </tr>
                    {expandedId === a.anomaly_id && (
                      <tr>
                        <td colSpan={6} style={{ background: 'var(--slate-50)', padding: '12px 20px' }}>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, fontSize: 12 }}>
                            <div><strong>Detector type:</strong> {a.detector_type}</div>
                            <div><strong>Threshold:</strong> {a.threshold_used ?? '—'}</div>
                            <div><strong>Original value:</strong> {a.original_value ?? '—'}</div>
                            <div><strong>Row index:</strong> {a.row_index ?? '—'}</div>
                            <div><strong>Anomaly ID:</strong> <code style={{ fontSize: 10 }}>{a.anomaly_id.slice(0, 12)}…</code></div>
                          </div>
                          <div style={{ marginTop: 8 }}>
                            <strong style={{ fontSize: 12 }}>Full explanation:</strong>
                            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{a.explanation}</p>
                          </div>
                          {a.surrounding_context && (
                            <div style={{ marginTop: 8 }}>
                              <strong style={{ fontSize: 12 }}>Surrounding context:</strong>
                              <pre style={{ fontSize: 10, background: 'var(--border-light)', padding: 8, borderRadius: 6, marginTop: 4, overflow: 'auto' }}>
                                {JSON.stringify(a.surrounding_context, null, 2)}
                              </pre>
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ padding: '0 22px' }}>
            <Pagination page={page} pageSize={PAGE_SIZE} total={filtered.length} onChange={setPage} />
          </div>
        </div>
      )}

      <div className="alert alert-info" style={{ marginTop: 20 }}>
        <span>ℹ</span>
        <span>Statistical anomalies are not confirmed equipment failures. Each detection must be interpreted in context and verified against other evidence before acting.</span>
      </div>
    </div>
  );
}
