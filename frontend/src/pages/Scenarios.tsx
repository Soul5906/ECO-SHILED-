// Scenarios page — load and run demo scenarios
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getScenarios, analyzeScenario } from '../services/api';
import { useAnalysis } from '../context/AnalysisContext';
import { LoadingSpinner, EmptyState, ErrorAlert, PageHeader } from '../components/Shared';
import type { ScenarioSummary } from '../types';

const TAG_COLORS: Record<string, string> = {
  baseline: 'badge-success', healthy: 'badge-success', reference: 'badge-blue',
  fault: 'badge-danger', degradation: 'badge-warning', sensor: 'badge-warning',
  weather: 'badge-info', communication: 'badge-warning', data_quality: 'badge-neutral',
  ambiguous: 'badge-neutral', edge_case: 'badge-neutral',
};

export default function Scenarios() {
  const navigate = useNavigate();
  const { setCurrentAnalysis, setDatasetRows } = useAnalysis();
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [running, setRunning] = useState<string | null>(null);
  const [runError, setRunError] = useState('');

  useEffect(() => {
    setLoading(true);
    getScenarios()
      .then(setScenarios)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleLoad = async (id: string) => {
    setRunning(id);
    setRunError('');
    try {
      const result = await analyzeScenario(id);
      setCurrentAnalysis(result);
      setDatasetRows([]);
      navigate('/');
    } catch (e: any) {
      setRunError(`Failed to run scenario "${id}": ${e.message}`);
    } finally {
      setRunning(null);
    }
  };

  return (
    <div>
      <PageHeader
        title="Demo Scenarios"
        subtitle="Load a reproducible synthetic dataset to explore ECO-SHIELD capabilities. All scenarios are clearly labelled as synthetic."
      />

      {loading && (
        <div className="flex items-center gap-2">
          <LoadingSpinner /><span className="text-secondary">Loading scenarios…</span>
        </div>
      )}
      {error && <ErrorAlert message={error} onRetry={() => { setError(''); setLoading(true); getScenarios().then(setScenarios).catch(e => setError(e.message)).finally(() => setLoading(false)); }} />}
      {runError && <div style={{ marginBottom: 16 }}><ErrorAlert message={runError} onRetry={() => setRunError('')} /></div>}

      {!loading && !error && scenarios.length === 0 && (
        <EmptyState title="No scenarios available" description="Check that the backend is running." />
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16, marginTop: 8 }}>
        {scenarios.map((s) => (
          <div key={s.id} className="card" style={{ display: 'flex', flexDirection: 'column' }}>
            <div className="card-header" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                <span className="card-title">{s.name}</span>
                <span className="badge badge-neutral" style={{ fontSize: 10 }}>Synthetic</span>
              </div>
              <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                {s.tags.map((t) => (
                  <span key={t} className={`badge ${TAG_COLORS[t] || 'badge-neutral'}`} style={{ fontSize: 10 }}>{t}</span>
                ))}
              </div>
            </div>
            <div className="card-body" style={{ flex: 1 }}>
              <p className="text-sm text-secondary" style={{ marginBottom: 12, lineHeight: 1.6 }}>{s.description}</p>
              <div style={{ display: 'flex', gap: 16, marginBottom: 12 }}>
                <div><span className="text-xs text-tertiary">Rows</span><div style={{ fontWeight: 600, fontSize: 14 }}>{s.row_count.toLocaleString()}</div></div>
                <div><span className="text-xs text-tertiary">Duration</span><div style={{ fontWeight: 600, fontSize: 14 }}>{s.duration_hours}h</div></div>
              </div>
              {s.injected_conditions.length > 0 && (
                <div className="text-xs text-secondary" style={{ marginBottom: 4 }}>
                  Injected: <strong>{s.injected_conditions.join(', ')}</strong>
                </div>
              )}
            </div>
            <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border-light)' }}>
              <button
                className="btn btn-primary w-full"
                onClick={() => handleLoad(s.id)}
                disabled={running === s.id}
              >
                {running === s.id ? (
                  <><LoadingSpinner size="sm" /> Running analysis…</>
                ) : (
                  '▶ Load & Analyse'
                )}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
