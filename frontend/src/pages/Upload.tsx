// Upload Data page — CSV upload with validation preview and analysis
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { validateCsv, analyzeCsv } from '../services/api';
import { useAnalysis } from '../context/AnalysisContext';
import {
  UploadZone, LoadingSpinner, ErrorAlert, PageHeader,
  Tabs, InfoRow,
} from '../components/Shared';
import type { DatasetValidationResponse } from '../types';

type Stage = 'idle' | 'validating' | 'validated' | 'analysing' | 'done' | 'error';

export default function Upload() {
  const navigate = useNavigate();
  const { setCurrentAnalysis, setDatasetRows } = useAnalysis();
  const [stage, setStage] = useState<Stage>('idle');
  const [validation, setValidation] = useState<DatasetValidationResponse | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('issues');
  const [showGuide, setShowGuide] = useState(false);

  const handleFile = async (f: File) => {
    setFile(f);
    setError('');
    setValidation(null);
    setStage('validating');
    try {
      const v = await validateCsv(f);
      setValidation(v);
      setStage('validated');
    } catch (e: any) {
      setError(e.message);
      setStage('error');
    }
  };

  const handleAnalyse = async () => {
    if (!file) return;
    setError('');
    setStage('analysing');
    try {
      const result = await analyzeCsv(file);
      setCurrentAnalysis(result);
      setDatasetRows(validation?.preview_rows ?? []);
      setStage('done');
      navigate('/');
    } catch (e: any) {
      setError(e.message);
      setStage('error');
    }
  };

  const resetUpload = () => {
    setStage('idle');
    setValidation(null);
    setFile(null);
    setError('');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <PageHeader
        title="Upload Telemetry Data"
        subtitle="Upload your solar telemetry CSV file for immediate validation, anomaly detection, and root-cause diagnosis."
        actions={
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setShowGuide((prev) => !prev)}
          >
            {showGuide ? 'Hide Format Guide' : 'CSV Format Guide'}
          </button>
        }
      />

      {/* Collapsible Format Reference */}
      {showGuide && (
        <div className="card">
          <div className="card-header">
            <div>
              <span className="card-title">Required & Supported CSV Schema</span>
              <p className="text-xs text-secondary" style={{ marginTop: 2 }}>
                Ensure your CSV headers match the exact names below. Missing values are gracefully reported without silent imputation.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setShowGuide(false)}
            >
              ✕
            </button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Column</th>
                    <th>Status</th>
                    <th>Example</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['timestamp', 'Required', '2024-06-01T06:00:00Z', 'ISO 8601 UTC timestamp format'],
                    ['power_kw', 'Required', '42.5', 'Active power output in kilowatts (kW)'],
                    ['irradiance_wm2', 'Required', '750.0', 'Solar irradiance in W/m² (GHI / POA)'],
                    ['temperature_c', 'Required', '28.3', 'Ambient or module temperature (°C)'],
                    ['inverter_id', 'Optional', 'INV-01', 'Inverter identifier for multi-string comparison'],
                    ['voltage_v', 'Optional', '400.2', 'DC string or AC output voltage (V)'],
                    ['current_a', 'Optional', '60.1', 'DC or AC electrical current (A)'],
                    ['humidity_pct', 'Optional', '65.0', 'Relative humidity percentage (0–100%)'],
                  ].map(([col, req, ex, notes]) => (
                    <tr key={col}>
                      <td><code style={{ fontSize: 12 }}>{col}</code></td>
                      <td>
                        <span className={`badge ${req === 'Required' ? 'badge-blue' : 'badge-neutral'}`}>
                          {req}
                        </span>
                      </td>
                      <td className="td-mono">{ex}</td>
                      <td className="text-sm text-secondary">{notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Upload Zone (Only when idle, validating, or error without validation) */}
      {!validation && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <UploadZone onFile={handleFile} loading={stage === 'validating'} />
          
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 10 }}>
              Required Data Columns
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
              <div style={{ background: '#ffffff', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '14px 16px', boxShadow: 'var(--shadow-xs)' }}>
                <span className="badge badge-blue" style={{ fontSize: 10, marginBottom: 6 }}>Required</span>
                <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>timestamp</div>
                <div style={{ fontSize: 11.5, color: 'var(--text-tertiary)', marginTop: 2 }}>ISO 8601 UTC format</div>
              </div>
              <div style={{ background: '#ffffff', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '14px 16px', boxShadow: 'var(--shadow-xs)' }}>
                <span className="badge badge-blue" style={{ fontSize: 10, marginBottom: 6 }}>Required</span>
                <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>power_kw</div>
                <div style={{ fontSize: 11.5, color: 'var(--text-tertiary)', marginTop: 2 }}>AC output power (kW)</div>
              </div>
              <div style={{ background: '#ffffff', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '14px 16px', boxShadow: 'var(--shadow-xs)' }}>
                <span className="badge badge-blue" style={{ fontSize: 10, marginBottom: 6 }}>Required</span>
                <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>irradiance_wm2</div>
                <div style={{ fontSize: 11.5, color: 'var(--text-tertiary)', marginTop: 2 }}>Solar irradiance (W/m²)</div>
              </div>
              <div style={{ background: '#ffffff', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '14px 16px', boxShadow: 'var(--shadow-xs)' }}>
                <span className="badge badge-blue" style={{ fontSize: 10, marginBottom: 6 }}>Required</span>
                <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>temperature_c</div>
                <div style={{ fontSize: 11.5, color: 'var(--text-tertiary)', marginTop: 2 }}>Ambient / module temp (°C)</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error Alert */}
      {stage === 'error' && error && (
        <ErrorAlert message={error} onRetry={resetUpload} />
      )}

      {/* Validation Results & Action Panel */}
      {validation && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Top Status & Action Bar */}
          <div className="card">
            <div className="card-header" style={{ flexWrap: 'wrap', gap: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span className={`badge ${validation.valid ? 'badge-success' : 'badge-warning'}`} style={{ padding: '6px 12px', fontSize: 12.5 }}>
                  {validation.valid ? '✓ Dataset Valid' : '⚠ Validation Notice'}
                </span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{file?.name}</div>
                  <div className="text-xs text-tertiary">
                    {file ? `${(file.size / 1024).toFixed(1)} KB` : ''} · {validation.row_count.toLocaleString()} rows verified
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginLeft: 'auto' }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={resetUpload}
                  disabled={stage === 'analysing'}
                >
                  Upload Different File
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleAnalyse}
                  disabled={stage === 'analysing'}
                >
                  {stage === 'analysing' ? (
                    <>
                      <LoadingSpinner size="sm" />
                      Analysing Pipeline…
                    </>
                  ) : (
                    'Run Full Analysis'
                  )}
                </button>
              </div>
            </div>

            {/* Validation Metrics */}
            <div className="card-body">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
                <div className="metric-card" style={{ padding: '12px 16px' }}>
                  <div className="metric-label">Verified Rows</div>
                  <div className="metric-value" style={{ fontSize: 20 }}>{validation.row_count.toLocaleString()}</div>
                </div>
                <div className="metric-card" style={{ padding: '12px 16px' }}>
                  <div className="metric-label">Columns</div>
                  <div className="metric-value" style={{ fontSize: 20 }}>{validation.column_names.length}</div>
                </div>
                <div className="metric-card" style={{ padding: '12px 16px' }}>
                  <div className="metric-label">Issues Found</div>
                  <div
                    className="metric-value"
                    style={{ fontSize: 20, color: validation.issues.length > 0 ? 'var(--rose-600)' : 'var(--text-primary)' }}
                  >
                    {validation.issues.length}
                  </div>
                </div>
                <div className="metric-card" style={{ padding: '12px 16px' }}>
                  <div className="metric-label">Warnings</div>
                  <div
                    className="metric-value"
                    style={{ fontSize: 20, color: validation.warnings.length > 0 ? 'var(--amber-600)' : 'var(--text-primary)' }}
                  >
                    {validation.warnings.length}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Analysing progress card */}
          {stage === 'analysing' && (
            <div className="card" style={{ padding: 40, textAlign: 'center' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
                <LoadingSpinner size="lg" />
                <div style={{ fontWeight: 600, fontSize: 16 }}>Running Diagnostics Pipeline…</div>
                <div className="text-sm text-secondary">
                  Data Quality Check → Statistical Anomaly Detection → Root-Cause Diagnosis → Test Recommendations
                </div>
              </div>
            </div>
          )}

          {/* Details Tabs */}
          <div className="card">
            <div className="card-header" style={{ paddingBottom: 0, borderBottom: 'none' }}>
              <Tabs
                tabs={[
                  { id: 'issues', label: `Issues (${validation.issues.length})` },
                  { id: 'warnings', label: `Warnings (${validation.warnings.length})` },
                  { id: 'preview', label: `Preview (${validation.preview_rows.length} rows)` },
                ]}
                active={activeTab}
                onChange={setActiveTab}
              />
            </div>
            <div className="card-body" style={{ paddingTop: 16 }}>
              {activeTab === 'issues' && (
                validation.issues.length === 0 ? (
                  <div className="alert alert-success">✓ No validation issues detected in this dataset.</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {validation.issues.map((issue, i) => (
                      <div key={i} className="alert alert-warning" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 6 }}>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                          <span className={`badge ${issue.severity === 'critical' ? 'badge-danger' : 'badge-warning'}`}>
                            {issue.severity}
                          </span>
                          <strong style={{ fontSize: 13 }}>{issue.issue_type}</strong>
                          {issue.column && (
                            <code style={{ fontSize: 11, background: 'var(--slate-200)', padding: '2px 6px', borderRadius: 4 }}>
                              {issue.column}
                            </code>
                          )}
                        </div>
                        <div className="text-sm">{issue.explanation}</div>
                        {issue.suggested_action && (
                          <div className="text-xs text-secondary">Recommended Action: {issue.suggested_action}</div>
                        )}
                      </div>
                    ))}
                  </div>
                )
              )}

              {activeTab === 'warnings' && (
                validation.warnings.length === 0 ? (
                  <div className="alert alert-success">✓ No warnings detected.</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {validation.warnings.map((w, i) => (
                      <div key={i} className="alert alert-info">{w}</div>
                    ))}
                  </div>
                )
              )}

              {activeTab === 'preview' && (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        {validation.column_names.map((c) => (
                          <th key={c}>{c}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {validation.preview_rows.map((row, i) => (
                        <tr key={i}>
                          {validation.column_names.map((c) => (
                            <td key={c} className="td-mono">
                              {row[c] === '' || row[c] === null || row[c] === undefined ? (
                                <span style={{ color: 'var(--rose-500)', fontStyle: 'italic', fontSize: 11 }}>
                                  missing
                                </span>
                              ) : (
                                String(row[c])
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
