// Diagnosis page — ranked hypotheses with evidence and uncertainty
import React, { useState } from 'react';
import { useAnalysis } from '../context/AnalysisContext';
import { EmptyState, PageHeader, DataSourceBanner } from '../components/Shared';
import { formatNumber } from '../utils/helpers';
import type { Hypothesis } from '../types';

function EvidenceList({ items, color, label }: { items: { description: string; evidence_type: string; value?: unknown; unit?: string }[]; color: string; label: string }) {
  if (items.length === 0) return null;
  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color, marginBottom: 4 }}>{label}</div>
      {items.map((e, i) => (
        <div key={i} style={{ display: 'flex', gap: 8, paddingLeft: 10, borderLeft: `2px solid ${color}`, marginBottom: 5 }}>
          <div>
            <span className="text-xs" style={{ background: 'var(--surface-2)', padding: '1px 6px', borderRadius: 4, marginRight: 6, fontWeight: 500 }}>
              {e.evidence_type.replace(/_/g, ' ')}
            </span>
            <span className="text-sm text-secondary">{e.description}</span>
            {e.value !== undefined && e.value !== null && (
              <span className="td-mono" style={{ marginLeft: 6, fontSize: 11, color: 'var(--text-tertiary)' }}>
                {String(e.value)}{e.unit ? ` ${e.unit}` : ''}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function HypothesisCard({ hyp, expanded, onToggle }: { hyp: Hypothesis; expanded: boolean; onToggle: () => void }) {
  const isFallback = hyp.rank > 900;
  return (
    <div className="hypothesis-card" style={{ opacity: isFallback ? 0.75 : 1 }}>
      <div className="hypothesis-header" onClick={onToggle}>
        <div className="rank-badge">{isFallback ? '?' : hyp.rank}</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{hyp.name}</div>
          {!isFallback && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div className="score-bar" style={{ maxWidth: 160 }}>
                <div className="score-bar-fill" style={{ width: `${Math.min(100, hyp.score)}%` }} />
              </div>
              <span className="text-xs text-tertiary">Score: {formatNumber(hyp.score, 1)}</span>
            </div>
          )}
        </div>
        {hyp.severity && (
          <span className="badge badge-neutral" style={{ fontSize: 11 }}>{hyp.severity}</span>
        )}
        <span style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>{expanded ? '▲' : '▼'}</span>
      </div>

      {expanded && (
        <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border-light)' }}>
          {/* Ranking explanation */}
          <div className="alert alert-info" style={{ marginBottom: 14 }}>
            
            <span className="text-sm">{hyp.ranking_explanation}</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <div>
              <EvidenceList items={hyp.supporting_evidence} color="var(--emerald-500)" label="Supporting Evidence" />
              <EvidenceList items={hyp.contradicting_evidence} color="var(--rose-500)" label="Contradicting Evidence" />
            </div>
            <div>
              {hyp.missing_measurements.length > 0 && (
                <div style={{ marginTop: 10 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--amber-600)', marginBottom: 4 }}>Missing Measurements</div>
                  {hyp.missing_measurements.map((m, i) => (
                    <div key={i} className="text-sm text-secondary" style={{ marginBottom: 3 }}>• {m}</div>
                  ))}
                </div>
              )}
              {hyp.required_assumptions.length > 0 && (
                <div style={{ marginTop: 10 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-tertiary)', marginBottom: 4 }}>Assumptions</div>
                  {hyp.required_assumptions.map((a, i) => (
                    <div key={i} className="text-sm text-secondary" style={{ marginBottom: 3 }}>• {a}</div>
                  ))}
                </div>
              )}
              {hyp.alternative_explanations.length > 0 && (
                <div style={{ marginTop: 10 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-tertiary)', marginBottom: 4 }}>Alternative Explanations</div>
                  {hyp.alternative_explanations.map((e, i) => (
                    <div key={i} className="text-sm text-secondary" style={{ marginBottom: 3 }}>• {e}</div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {hyp.recommended_verification && (
            <div style={{ marginTop: 14, padding: '10px 14px', background: 'var(--accent-light)', borderRadius: 8, borderLeft: '3px solid var(--accent)' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)', marginBottom: 2 }}>Recommended Verification</div>
              <div className="text-sm">{hyp.recommended_verification}</div>
            </div>
          )}

          <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {hyp.triggered_rule_ids.map((r) => (
              <span key={r} className="badge badge-blue">{r}</span>
            ))}
            {hyp.input_features_used.map((f) => (
              <span key={f} className="badge badge-neutral">{f}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Diagnosis() {
  const { currentAnalysis } = useAnalysis();
  const [expanded, setExpanded] = useState<string | null>(null);

  if (!currentAnalysis) {
    return (
      <div>
        <PageHeader title="Root-Cause Diagnosis" subtitle="Run an analysis to see ranked diagnostic hypotheses." />
        <EmptyState title="No analysis loaded" description="Load a demo scenario or upload a CSV." />
      </div>
    );
  }

  const diag = currentAnalysis.diagnosis;
  const hypotheses = diag?.hypotheses ?? [];
  const active = hypotheses.filter((h) => h.rank < 900);
  const fallback = hypotheses.find((h) => h.rank >= 900);

  return (
    <div>
      <PageHeader
        title="Root-Cause Diagnosis"
        subtitle={`${active.length} active hypotheses · evidence-based ranking`}
      />
      <DataSourceBanner source={currentAnalysis.source} />

      {/* Uncertainty note */}
      {diag?.uncertainty_note && (
        <div className="alert alert-warning" style={{ marginBottom: 20 }}>
          
          <span className="text-sm">{diag.uncertainty_note}</span>
        </div>
      )}

      {/* Insufficient evidence banner */}
      {diag?.insufficient_evidence && (
        <div className="alert alert-info" style={{ marginBottom: 20 }}>
          <div>
            <strong>Insufficient evidence for a specific diagnosis.</strong>
            <div className="text-sm" style={{ marginTop: 4 }}>The available data does not provide enough signal to distinguish between specific fault types. Collect more data or add missing measurement channels before drawing conclusions.</div>
          </div>
        </div>
      )}

      {/* Competing causes note */}
      {diag?.competing_causes_note && active.length > 1 && (
        <div className="text-sm text-secondary" style={{ marginBottom: 16, padding: '8px 14px', background: 'var(--surface-2)', borderRadius: 8 }}>
          {diag.competing_causes_note}
        </div>
      )}

      {/* Hypotheses */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {active.map((h) => (
          <HypothesisCard
            key={h.hypothesis_id}
            hyp={h}
            expanded={expanded === h.hypothesis_id}
            onToggle={() => setExpanded(expanded === h.hypothesis_id ? null : h.hypothesis_id)}
          />
        ))}
        {fallback && (
          <HypothesisCard
            hyp={fallback}
            expanded={expanded === fallback.hypothesis_id}
            onToggle={() => setExpanded(expanded === fallback.hypothesis_id ? null : fallback.hypothesis_id)}
          />
        )}
        {hypotheses.length === 0 && (
          <EmptyState icon="🩺" title="No hypotheses generated" description="Run the analysis pipeline to generate diagnostic results." />
        )}
      </div>

      {/* Limitations */}
      {currentAnalysis.limitations?.length > 0 && (
        <div className="alert alert-info" style={{ marginTop: 20 }}>
          
          <div>
            <strong>Analysis limitations:</strong>
            <ul style={{ marginTop: 4, paddingLeft: 16 }}>
              {currentAnalysis.limitations.map((l, i) => <li key={i} className="text-sm">{l}</li>)}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
