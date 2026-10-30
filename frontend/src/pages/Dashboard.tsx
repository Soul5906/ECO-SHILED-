// Dashboard page — Overview with metrics, charts, and latest analysis
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getHealth } from '../services/api';
import { useAnalysis } from '../context/AnalysisContext';
import {
  LoadingSpinner, EmptyState, ErrorAlert, OfflineAlert,
  QualityScoreRing, SourceChip, DataSourceBanner, PageHeader, InfoRow,
} from '../components/Shared';
import { PowerIrradianceChart, TemperatureChart, ColumnQualityMiniBar } from '../components/Charts';
import { formatNumber, formatDate, severityBadgeClass } from '../utils/helpers';
import type { HealthResponse } from '../types';

export default function Dashboard() {
  const { currentAnalysis, datasetRows, clearAnalysis } = useAnalysis();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthErr, setHealthErr] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getHealth()
      .then((h) => { setHealth(h); setHealthErr(false); })
      .catch(() => setHealthErr(true))
      .finally(() => setLoading(false));
  }, []);

  const qa = currentAnalysis?.quality_report;
  const an = currentAnalysis?.anomaly_summary;
  const diag = currentAnalysis?.diagnosis;
  const topHyp = diag?.hypotheses?.find((h) => h.rank === 1 && h.rank < 900);

  // Build chart data from dataset rows
  const chartData = datasetRows.slice(0, 500).map((r) => ({
    timestamp: r.timestamp as string,
    power_kw: typeof r.power_kw === 'number' ? r.power_kw : undefined,
    irradiance_wm2: typeof r.irradiance_wm2 === 'number' ? r.irradiance_wm2 : undefined,
    temperature_c: typeof r.temperature_c === 'number' ? r.temperature_c : undefined,
  }));

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="ECO-SHIELD Solar Diagnostics — evidence-driven analysis"
        actions={
          <div className="flex gap-2">
            <Link to="/scenarios" className="btn btn-primary btn-sm">Load Scenario</Link>
            <Link to="/upload" className="btn btn-secondary btn-sm">Upload CSV</Link>
            {currentAnalysis && (
              <button className="btn btn-ghost btn-sm" onClick={clearAnalysis} title="Clear current analysis">Clear</button>
            )}
          </div>
        }
      />

      {/* Backend status */}
      {loading && <div className="flex items-center gap-2 mb-4"><LoadingSpinner /><span className="text-secondary text-sm">Connecting to backend…</span></div>}
      {healthErr && !loading && <OfflineAlert />}


      {!currentAnalysis ? (
        <EmptyState
          icon={
            <img
              src="/logo.png"
              alt="ECO-SHIELD"
              style={{ maxWidth: 160, maxHeight: 90, objectFit: 'contain', marginBottom: 10 }}
            />
          }
          title="No analysis loaded"
          description="Load a demo scenario or upload a CSV file to begin analysing solar telemetry."
          action={
            <div className="flex gap-2">
              <Link to="/scenarios" className="btn btn-primary">Load Demo Scenario</Link>
              <Link to="/upload" className="btn btn-secondary">Upload CSV</Link>
            </div>
          }
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Data source banner */}
          <DataSourceBanner source={currentAnalysis.source} />

          {/* Meta row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <SourceChip source={currentAnalysis.source} />
            <span className="text-sm text-secondary">Analysis: <strong style={{ color: 'var(--text-primary)', fontFamily: 'monospace' }}>{currentAnalysis.analysis_id.slice(0, 8)}</strong></span>
            <span className="text-sm text-secondary">Run: {formatDate(currentAnalysis.created_at)}</span>
            <span className={`badge ${currentAnalysis.status === 'complete' ? 'badge-success' : 'badge-warning'}`}>{currentAnalysis.status}</span>
          </div>

          {/* Key metrics */}
          <div className="metric-grid">
            <div className="metric-card">
              <div className="metric-label">Quality Score</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <QualityScoreRing score={qa?.quality_score ?? 0} size={56} />
                <div>
                  <div className="metric-value" style={{ fontSize: 20 }}>{formatNumber(qa?.quality_score ?? 0, 0)}<span style={{ fontSize: 13, fontWeight: 400 }}>/100</span></div>
                  <div className="metric-sub">Diagnostic Score</div>
                </div>
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Total Rows</div>
              <div className="metric-value">{qa?.total_rows?.toLocaleString() ?? '—'}</div>
              <div className="metric-sub">{formatNumber(qa?.completeness_pct, 1)}% complete</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Anomalies</div>
              <div className="metric-value">{an?.total_anomalies ?? '—'}</div>
              <div className="metric-sub">{an?.detectors_run?.length ?? 0} detectors run</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Invalid Timestamps</div>
              <div className="metric-value">{qa?.invalid_timestamp_count ?? '—'}</div>
              <div className="metric-sub">{qa?.duplicate_timestamps ?? 0} duplicates</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Data Gaps</div>
              <div className="metric-value">{qa?.missing_periods ?? '—'}</div>
              <div className="metric-sub">{qa?.irregular_intervals ?? 0} irregular intervals</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Hypotheses</div>
              <div className="metric-value">{diag?.hypotheses?.filter((h) => h.rank < 900).length ?? '—'}</div>
              <div className="metric-sub">{diag?.insufficient_evidence ? 'Insufficient evidence' : 'Ranked'}</div>
            </div>
          </div>

          {/* Charts */}
          {chartData.length > 0 && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">Power & Irradiance</span>
                <span className="text-xs text-tertiary">First 500 rows shown · all values are dataset values</span>
              </div>
              <div className="card-body">
                <PowerIrradianceChart data={chartData} />
              </div>
            </div>
          )}

          {chartData.length > 0 && (
            <div className="card">
              <div className="card-header"><span className="card-title">Temperature</span></div>
              <div className="card-body">
                <TemperatureChart data={chartData} />
              </div>
            </div>
          )}

          {/* Column quality breakdown */}
          {qa?.column_quality && qa.column_quality.length > 0 && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">Column Quality</span>
                <span className="text-xs text-tertiary">Missing, invalid and range violations per column</span>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Column</th>
                      <th>Type</th>
                      <th>Completeness</th>
                      <th>Invalid</th>
                      <th>Negatives</th>
                      <th>Range violations</th>
                    </tr>
                  </thead>
                  <tbody>
                    {qa.column_quality.map((cq) => {
                      const completePct = 100 - cq.missing_pct;
                      return (
                        <tr key={cq.column}>
                          <td><code style={{ fontSize: 12 }}>{cq.column}</code></td>
                          <td className="text-xs text-tertiary">{cq.dtype}</td>
                          <td style={{ minWidth: 140 }}><ColumnQualityMiniBar pct={completePct} /></td>
                          <td style={{ fontWeight: cq.invalid_count > 0 ? 700 : 400, color: cq.invalid_count > 0 ? 'var(--rose-600)' : 'var(--text-primary)' }}>{cq.invalid_count}</td>
                          <td>{cq.negative_count}</td>
                          <td style={{ fontWeight: cq.range_violations > 0 ? 700 : 400, color: cq.range_violations > 0 ? 'var(--amber-600)' : 'var(--text-primary)' }}>{cq.range_violations}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {topHyp && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">Top Hypothesis</span>
                <Link to="/diagnosis" className="btn btn-ghost btn-sm">View all →</Link>
              </div>
              <div className="card-body">
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                  <div className="rank-badge">1</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, marginBottom: 6 }}>{topHyp.name}</div>
                    <div className="text-sm text-secondary" style={{ marginBottom: 8 }}>
                      Confidence score: <strong>{formatNumber(topHyp.score, 1)}</strong> — {topHyp.ranking_explanation}
                    </div>
                    <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 4 }}>Supporting evidence:</div>
                    {topHyp.supporting_evidence.slice(0, 2).map((e, i) => (
                      <div key={i} className="text-sm text-secondary" style={{ paddingLeft: 10, borderLeft: '2px solid var(--emerald-500)', marginBottom: 4 }}>
                        {e.description}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Top recommendation */}
          {currentAnalysis.recommendations?.[0] && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">Next Recommended Test</span>
                <Link to="/recommendations" className="btn btn-ghost btn-sm">View all →</Link>
              </div>
              <div className="card-body">
                <div className="rec-card" style={{ border: 'none', padding: 0 }}>
                  <div className="rec-priority-dot" style={{ background: currentAnalysis.recommendations[0].priority === 'high' ? 'var(--rose-500)' : 'var(--amber-500)' }} />
                  <div>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>{currentAnalysis.recommendations[0].test_name}</div>
                    <div className="text-sm text-secondary">{currentAnalysis.recommendations[0].reason}</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Warnings */}
          {currentAnalysis.warnings?.length > 0 && (
            <div className="alert alert-warning">
              <span></span>
              <div>
                <strong>Analysis warnings:</strong>
                <ul style={{ marginTop: 4, paddingLeft: 16 }}>
                  {currentAnalysis.warnings.map((w, i) => <li key={i} className="text-sm">{w}</li>)}
                </ul>
              </div>
            </div>
          )}

          {/* Quick links */}
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {[
              { to: '/anomalies', label: 'Anomalies' },
              { to: '/diagnosis', label: 'Diagnosis' },
              { to: '/recommendations', label: 'Recommendations' },
              { to: '/explorer', label: 'Data Explorer' },
              { to: '/history', label: 'History' },
            ].map((l) => (
              <Link key={l.to} to={l.to} className="btn btn-secondary btn-sm">{l.label}</Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
