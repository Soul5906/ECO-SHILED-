// Report History page — list, open, compare, download past analyses
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAnalyses, getAnalysis, downloadReport, downloadAnomalyCsv, compareAnalyses } from '../services/api';
import { useAnalysis } from '../context/AnalysisContext';
import { LoadingSpinner, EmptyState, ErrorAlert, PageHeader, SourceChip, Pagination } from '../components/Shared';
import { formatDate, formatRelative, qualityScoreColor } from '../utils/helpers';
import type { AnalysisSummary, CompareResponse } from '../types';

const PAGE_SIZE = 20;

export default function History() {
  const navigate = useNavigate();
  const { setCurrentAnalysis } = useAnalysis();
  const [summaries, setSummaries] = useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [sourceFilter, setSourceFilter] = useState('all');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [comparing, setComparing] = useState(false);
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [opening, setOpening] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError('');
    getAnalyses({ source: sourceFilter === 'all' ? undefined : sourceFilter, limit: 200 })
      .then(setSummaries)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [sourceFilter]);

  const pageData = summaries.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const openAnalysis = async (id: string) => {
    setOpening(id);
    try {
      const result = await getAnalysis(id);
      setCurrentAnalysis(result);
      navigate('/');
    } catch (e: any) {
      alert(`Failed to load analysis: ${e.message}`);
    } finally {
      setOpening(null);
    }
  };

  const handleDownload = async (id: string, type: 'json' | 'csv') => {
    setDownloading(id);
    try {
      if (type === 'json') await downloadReport(id);
      else await downloadAnomalyCsv(id);
    } catch (e: any) {
      alert(`Download failed: ${e.message}`);
    } finally {
      setDownloading(null);
    }
  };

  const handleCompare = async () => {
    if (selected.size !== 2) return;
    const [a, b] = Array.from(selected);
    setComparing(true);
    try {
      const r = await compareAnalyses(a, b);
      setCompareResult(r);
    } catch (e: any) {
      alert(`Comparison failed: ${e.message}`);
    } finally {
      setComparing(false);
    }
  };

  const toggleSelect = (id: string) => {
    const s = new Set(selected);
    if (s.has(id)) s.delete(id);
    else if (s.size < 2) s.add(id);
    else { s.clear(); s.add(id); }
    setSelected(s);
    setCompareResult(null);
  };

  return (
    <div>
      <PageHeader
        title="Report History"
        subtitle="All past analyses — persisted in SQLite. Click to reload, download, or compare."
        actions={
          <div className="flex gap-2">
            <button className="btn btn-secondary btn-sm" onClick={load}>↺ Refresh</button>
            {selected.size === 2 && (
              <button className="btn btn-primary btn-sm" onClick={handleCompare} disabled={comparing}>
                {comparing ? <LoadingSpinner size="sm" /> : null}
                Compare Selected
              </button>
            )}
          </div>
        }
      />

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        <select className="input select" style={{ maxWidth: 160 }} value={sourceFilter} onChange={(e) => { setSourceFilter(e.target.value); setPage(1); }}>
          <option value="all">All sources</option>
          <option value="demo">Demo</option>
          <option value="upload">Upload</option>
        </select>
        {selected.size > 0 && (
          <span className="text-sm text-secondary" style={{ lineHeight: '36px' }}>
            {selected.size} selected — {selected.size < 2 ? 'select 1 more to compare' : 'ready to compare'}
          </span>
        )}
      </div>

      {loading && <div className="flex gap-2 items-center"><LoadingSpinner /><span className="text-secondary">Loading history…</span></div>}
      {error && <ErrorAlert message={error} onRetry={load} />}

      {/* Comparison result */}
      {compareResult && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <span className="card-title">Comparison Result</span>
            <button className="btn btn-ghost btn-sm" onClick={() => setCompareResult(null)}>✕</button>
          </div>
          <div className="card-body" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <div>
              <div style={{ fontWeight: 600, marginBottom: 8, color: 'var(--accent)' }}>First: {compareResult.first_id.slice(0, 8)}</div>
              <div className="text-sm">Quality: <strong>{compareResult.first_summary.quality_score}</strong></div>
              <div className="text-sm">Anomalies: <strong>{compareResult.first_summary.anomaly_count}</strong></div>
              <div className="text-sm">Top hypothesis: {compareResult.first_summary.top_hypothesis ?? '—'}</div>
            </div>
            <div>
              <div style={{ fontWeight: 600, marginBottom: 8, color: 'var(--accent)' }}>Second: {compareResult.second_id.slice(0, 8)}</div>
              <div className="text-sm">Quality: <strong>{compareResult.second_summary.quality_score}</strong></div>
              <div className="text-sm">Anomalies: <strong>{compareResult.second_summary.anomaly_count}</strong></div>
              <div className="text-sm">Top hypothesis: {compareResult.second_summary.top_hypothesis ?? '—'}</div>
            </div>
            <div style={{ gridColumn: '1/-1', paddingTop: 12, borderTop: '1px solid var(--border-light)' }}>
              <div className="text-sm text-secondary">Quality Δ: <strong style={{ color: Number(compareResult.differences.quality_score_delta) >= 0 ? 'var(--emerald-600)' : 'var(--rose-600)' }}>{Number(compareResult.differences.quality_score_delta) > 0 ? '+' : ''}{String(compareResult.differences.quality_score_delta ?? '')}</strong></div>
              <div className="text-sm text-secondary">Anomaly Δ: <strong>{(Number(compareResult.differences.anomaly_count_delta) > 0 ? '+' : '') + String(compareResult.differences.anomaly_count_delta ?? '')}</strong></div>
            </div>
          </div>
        </div>
      )}

      {!loading && summaries.length === 0 && !error && (
        <EmptyState title="No analyses yet" description="Run a scenario or upload a CSV to create your first analysis." />
      )}

      {summaries.length > 0 && (
        <div className="card">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Select</th>
                  <th>ID</th>
                  <th>Source</th>
                  <th>When</th>
                  <th>Quality</th>
                  <th>Anomalies</th>
                  <th>Rows</th>
                  <th>Top Hypothesis</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {pageData.map((s) => (
                  <tr key={s.analysis_id} style={selected.has(s.analysis_id) ? { background: 'var(--accent-light)' } : undefined}>
                    <td>
                      <input type="checkbox" checked={selected.has(s.analysis_id)} onChange={() => toggleSelect(s.analysis_id)} />
                    </td>
                    <td className="td-mono text-xs">{s.analysis_id.slice(0, 8)}…</td>
                    <td><SourceChip source={s.source} /></td>
                    <td>
                      <div className="text-sm">{formatRelative(s.created_at)}</div>
                      <div className="text-xs text-tertiary">{formatDate(s.created_at)}</div>
                    </td>
                    <td>
                      <span style={{ fontWeight: 700, color: qualityScoreColor(s.quality_score), fontSize: 15 }}>
                        {s.quality_score.toFixed(0)}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{s.anomaly_count}</td>
                    <td>{s.row_count.toLocaleString()}</td>
                    <td className="text-sm" style={{ maxWidth: 200 }}>
                      {s.top_hypothesis ? <span className="truncate">{s.top_hypothesis}</span> : <span className="text-tertiary">—</span>}
                    </td>
                    <td>
                      <div className="flex gap-2">
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => openAnalysis(s.analysis_id)}
                          disabled={opening === s.analysis_id}
                        >
                          {opening === s.analysis_id ? <LoadingSpinner size="sm" /> : 'Open'}
                        </button>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleDownload(s.analysis_id, 'json')}
                          disabled={downloading === s.analysis_id}
                          title="Download JSON report"
                        >
                          JSON
                        </button>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleDownload(s.analysis_id, 'csv')}
                          disabled={downloading === s.analysis_id}
                          title="Download anomaly CSV"
                        >
                          CSV
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ padding: '0 22px' }}>
            <Pagination page={page} pageSize={PAGE_SIZE} total={summaries.length} onChange={setPage} />
          </div>
        </div>
      )}
    </div>
  );
}
