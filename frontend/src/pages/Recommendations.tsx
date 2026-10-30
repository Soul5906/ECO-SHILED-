// Recommendations page
import React from 'react';
import { useAnalysis } from '../context/AnalysisContext';
import { EmptyState, PageHeader, DataSourceBanner } from '../components/Shared';
import { priorityColor } from '../utils/helpers';
import type { Recommendation } from '../types';

function RecCard({ rec }: { rec: Recommendation }) {
  const color = priorityColor(rec.priority);
  return (
    <div className="card">
      <div className="card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1 }}>
          <div className="rec-priority-dot" style={{ background: color }} />
          <span className="card-title">{rec.test_name}</span>
        </div>
        <span className="badge" style={{ background: `${color}20`, color }}>{rec.priority}</span>
      </div>
      <div className="card-body">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: 'var(--text-secondary)' }}>Why This Test</div>
            <p className="text-sm">{rec.reason}</p>

            <div style={{ fontSize: 12, fontWeight: 600, marginTop: 12, marginBottom: 4, color: 'var(--text-secondary)' }}>Hypotheses Addressed</div>
            <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
              {rec.hypotheses_addressed.map((h) => (
                <span key={h} className="badge badge-blue" style={{ fontSize: 11 }}>{h}</span>
              ))}
            </div>

            {rec.evidence_required?.length > 0 && (
              <>
                <div style={{ fontSize: 12, fontWeight: 600, marginTop: 12, marginBottom: 4, color: 'var(--text-secondary)' }}>Evidence Required</div>
                {rec.evidence_required.map((e, i) => (
                  <div key={i} className="text-sm text-secondary">• {e}</div>
                ))}
              </>
            )}
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: 'var(--text-secondary)' }}>Expected Observation</div>
            <p className="text-sm">{rec.expected_observation}</p>

            <div style={{ fontSize: 12, fontWeight: 600, marginTop: 12, marginBottom: 4, color: 'var(--text-secondary)' }}>How This Changes the Diagnosis</div>
            <p className="text-sm">{rec.how_result_changes_diagnosis}</p>

            {rec.estimated_effort && (
              <div style={{ marginTop: 12 }}>
                <span className="badge badge-neutral">Effort: {rec.estimated_effort}</span>
              </div>
            )}
          </div>
        </div>

        {rec.safety_note && (
          <div className="alert alert-warning" style={{ marginTop: 14 }}>
            <span className="text-sm"><strong>Safety note:</strong> {rec.safety_note}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Recommendations() {
  const { currentAnalysis } = useAnalysis();
  const recs = currentAnalysis?.recommendations ?? [];

  if (!currentAnalysis) {
    return (
      <div>
        <PageHeader title="Next-Best-Test Recommendations" subtitle="Run an analysis to receive diagnostic test recommendations." />
        <EmptyState title="No analysis loaded" description="Load a demo scenario or upload a CSV." />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Next-Best-Test Recommendations"
        subtitle={`${recs.length} recommended diagnostic test${recs.length !== 1 ? 's' : ''} based on current hypotheses`}
      />
      <DataSourceBanner source={currentAnalysis.source} />

      <div className="alert alert-info" style={{ marginBottom: 20 }}>
        <span className="text-sm">Recommendations are based on current telemetry analysis results. Physical verification must be conducted by qualified personnel using appropriate safety protocols.</span>
      </div>

      {recs.length === 0 ? (
        <EmptyState title="No recommendations generated" description="Run the analysis pipeline to generate recommendations." />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {recs.map((r) => <RecCard key={r.recommendation_id} rec={r} />)}
        </div>
      )}
    </div>
  );
}
