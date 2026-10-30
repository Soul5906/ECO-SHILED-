// Frontend tests for ECO-SHIELD
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock API calls
vi.mock('../services/api', () => ({
  getHealth: vi.fn().mockResolvedValue({ status: 'ok', version: '1.0.0', timestamp: new Date().toISOString(), database: 'ok' }),
  getScenarios: vi.fn().mockResolvedValue([
    { id: 'normal_operation', name: 'Normal Operation', description: 'Healthy solar array', tags: ['baseline'], row_count: 288, duration_hours: 72, injected_conditions: [] },
    { id: 'power_decline', name: 'Power Decline', description: 'Declining power', tags: ['fault'], row_count: 480, duration_hours: 120, injected_conditions: ['power_decline_trend'] },
  ]),
  analyzeScenario: vi.fn().mockResolvedValue({
    analysis_id: 'test-id-1234',
    status: 'complete',
    created_at: new Date().toISOString(),
    dataset_id: 'ds-1',
    source: 'demo',
    algorithm_version: '1.0.0',
    configuration_used: {},
    quality_report: { total_rows: 288, quality_score: 85.5, completeness_pct: 99.2, valid_timestamp_count: 288, invalid_timestamp_count: 0, out_of_order_timestamps: 0, duplicate_timestamps: 0, duplicate_records: 0, missing_periods: 0, irregular_intervals: 0, column_quality: [], quality_score_method: 'Heuristic', issues: [], transformations_applied: [] },
    anomaly_summary: { total_anomalies: 3, by_severity: { low: 2, medium: 1 }, by_detector: { mad_outlier: 3 }, detectors_run: ['mad_outlier'], anomalies: [
      { anomaly_id: 'a1', detector_name: 'mad_outlier', detector_type: 'statistical', column: 'power_kw', timestamp: new Date().toISOString(), row_index: 50, measured_value: 99.9, threshold_used: 3.5, severity: 'medium', explanation: 'Outlier detected in power_kw' },
    ]},
    diagnosis: { hypotheses: [{ hypothesis_id: 'h1', name: 'Normal Operation', rank: 1, score: 20.0, supporting_evidence: [], contradicting_evidence: [], required_assumptions: [], missing_measurements: [], alternative_explanations: [], recommended_verification: 'None', ranking_explanation: 'Low anomaly count', triggered_rule_ids: [], input_features_used: [] }], uncertainty_note: 'Heuristic scores only.', competing_causes_note: 'Multiple may coexist.', insufficient_evidence: false, evidence_summary: {} },
    recommendations: [{ recommendation_id: 'r1', test_name: 'Collect More Data', reason: 'Baseline', hypotheses_addressed: [], evidence_required: [], expected_observation: '', how_result_changes_diagnosis: '', priority: 'low' }],
    warnings: [],
    limitations: ['Heuristic scores only'],
  }),
  getAnalyses: vi.fn().mockResolvedValue([]),
  getSettings: vi.fn().mockResolvedValue({
    anomaly_thresholds: { mad_threshold: 3.5, zscore_threshold: 3.0, rate_of_change_threshold: 50.0, gap_minutes: 30.0, flatline_minutes: 60.0, power_irradiance_drop_ratio: 0.5 },
    physical_limits: { max_power_kw: 10000, max_irradiance_wm2: 1500, min_temperature_c: -50, max_temperature_c: 100, max_voltage_v: 1500, max_current_a: 1000 },
    default_timezone: 'UTC',
    expected_interval_minutes: 15,
    max_upload_size_mb: 50,
    max_rows: 100000,
    active_detectors: ['mad_outlier', 'zscore_outlier'],
    active_rules: ['telemetry_failure'],
    report_retention_days: 90,
  }),
  updateSettings: vi.fn().mockResolvedValue({}),
  validateCsv: vi.fn().mockResolvedValue({ valid: true, dataset_id: 'ds-2', row_count: 10, column_names: ['timestamp', 'power_kw', 'irradiance_wm2', 'temperature_c'], issues: [], warnings: [], preview_rows: [] }),
  analyzeCsv: vi.fn().mockResolvedValue({}),
  downloadReport: vi.fn().mockResolvedValue(undefined),
  downloadAnomalyCsv: vi.fn().mockResolvedValue(undefined),
  compareAnalyses: vi.fn().mockResolvedValue({}),
}));

import { AnalysisProvider } from '../context/AnalysisContext';
import Dashboard from '../pages/Dashboard';
import Scenarios from '../pages/Scenarios';
import Anomalies from '../pages/Anomalies';
import Diagnosis from '../pages/Diagnosis';
import Recommendations from '../pages/Recommendations';
import History from '../pages/History';
import Settings from '../pages/Settings';
import { LoadingSpinner, EmptyState, ErrorAlert, SeverityBadge, QualityScoreRing } from '../components/Shared';

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <MemoryRouter>
      <AnalysisProvider>{children}</AnalysisProvider>
    </MemoryRouter>
  );
}

// ── Component unit tests ─────────────────────────────────────────────────────

describe('LoadingSpinner', () => {
  it('renders with default size', () => {
    const { container } = render(<LoadingSpinner />);
    expect(container.querySelector('.spinner')).toBeTruthy();
  });

  it('renders large size', () => {
    const { container } = render(<LoadingSpinner size="lg" />);
    expect(container.querySelector('.spinner-lg')).toBeTruthy();
  });
});

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(<EmptyState title="No data" description="Upload a file" />);
    expect(screen.getByText('No data')).toBeTruthy();
    expect(screen.getByText('Upload a file')).toBeTruthy();
  });

  it('renders action button', () => {
    render(<EmptyState title="Empty" action={<button>Act</button>} />);
    expect(screen.getByText('Act')).toBeTruthy();
  });
});

describe('ErrorAlert', () => {
  it('shows error message', () => {
    render(<ErrorAlert message="Something went wrong" />);
    expect(screen.getByText(/Something went wrong/)).toBeTruthy();
  });

  it('shows retry button when provided', () => {
    const retry = vi.fn();
    render(<ErrorAlert message="Err" onRetry={retry} />);
    fireEvent.click(screen.getByText('Retry'));
    expect(retry).toHaveBeenCalled();
  });
});

describe('SeverityBadge', () => {
  it.each(['critical', 'high', 'medium', 'low', 'info'])('renders %s severity', (sev) => {
    render(<SeverityBadge severity={sev as any} />);
    expect(screen.getByText(sev)).toBeTruthy();
  });
});

describe('QualityScoreRing', () => {
  it('renders SVG ring with score', () => {
    const { container } = render(<QualityScoreRing score={78} />);
    expect(container.querySelector('svg')).toBeTruthy();
    expect(screen.getByText('78')).toBeTruthy();
  });

  it('renders 0 score', () => {
    render(<QualityScoreRing score={0} />);
    expect(screen.getByText('0')).toBeTruthy();
  });

  it('renders 100 score', () => {
    render(<QualityScoreRing score={100} />);
    expect(screen.getByText('100')).toBeTruthy();
  });
});

// ── Dashboard tests ──────────────────────────────────────────────────────────

describe('Dashboard', () => {
  it('shows empty state when no analysis loaded', () => {
    render(<Wrapper><Dashboard /></Wrapper>);
    expect(screen.getByText(/No analysis loaded/)).toBeTruthy();
  });

  it('shows links to scenarios and upload', () => {
    render(<Wrapper><Dashboard /></Wrapper>);
    expect(screen.getByText(/Load Demo Scenario/)).toBeTruthy();
    expect(screen.getAllByText(/Upload CSV/).length).toBeGreaterThan(0);
  });

  it('connects to backend on mount', async () => {
    const { getHealth } = await import('../services/api');
    render(<Wrapper><Dashboard /></Wrapper>);
    await waitFor(() => expect(getHealth).toHaveBeenCalled());
  });

  it('shows offline alert when backend unreachable', async () => {
    const { getHealth } = await import('../services/api');
    (getHealth as any).mockRejectedValueOnce(new Error('Network error'));
    render(<Wrapper><Dashboard /></Wrapper>);
    await waitFor(() => expect(screen.getByText(/Backend Unavailable/)).toBeTruthy());
  });
});

// ── Scenarios tests ───────────────────────────────────────────────────────────

describe('Scenarios', () => {
  it('loads and displays scenarios', async () => {
    render(<Wrapper><Scenarios /></Wrapper>);
    await waitFor(() => expect(screen.getByText('Normal Operation')).toBeTruthy());
    expect(screen.getByText('Power Decline')).toBeTruthy();
  });

  it('shows scenario row count', async () => {
    render(<Wrapper><Scenarios /></Wrapper>);
    await waitFor(() => expect(screen.getByText('288')).toBeTruthy());
  });

  it('shows Load button for each scenario', async () => {
    render(<Wrapper><Scenarios /></Wrapper>);
    await waitFor(() => {
      const btns = screen.getAllByText(/Load & Analyse/);
      expect(btns.length).toBeGreaterThan(0);
    });
  });
});

// ── Anomalies tests ───────────────────────────────────────────────────────────

describe('Anomalies page — no analysis', () => {
  it('shows empty state', () => {
    render(<Wrapper><Anomalies /></Wrapper>);
    expect(screen.getByText(/No analysis loaded/)).toBeTruthy();
  });
});

// ── Diagnosis page tests ──────────────────────────────────────────────────────

describe('Diagnosis page — no analysis', () => {
  it('shows empty state', () => {
    render(<Wrapper><Diagnosis /></Wrapper>);
    expect(screen.getByText(/No analysis loaded/)).toBeTruthy();
  });
});

// ── Recommendations page tests ────────────────────────────────────────────────

describe('Recommendations — no analysis', () => {
  it('shows empty state', () => {
    render(<Wrapper><Recommendations /></Wrapper>);
    expect(screen.getByText(/No analysis loaded/)).toBeTruthy();
  });
});

// ── History tests ─────────────────────────────────────────────────────────────

describe('History', () => {
  it('shows empty state when no analyses', async () => {
    render(<Wrapper><History /></Wrapper>);
    await waitFor(() => expect(screen.getByText(/No analyses yet/)).toBeTruthy());
  });
});

// ── Settings tests ────────────────────────────────────────────────────────────

describe('Settings', () => {
  it('loads and displays settings form', async () => {
    render(<Wrapper><Settings /></Wrapper>);
    await waitFor(() => expect(screen.getByText(/Anomaly Detection Thresholds/)).toBeTruthy());
  });

  it('shows Save button', async () => {
    render(<Wrapper><Settings /></Wrapper>);
    await waitFor(() => expect(screen.getByText('Save Settings')).toBeTruthy());
  });

  it('shows physical limits section', async () => {
    render(<Wrapper><Settings /></Wrapper>);
    await waitFor(() => expect(screen.getByText(/Physical Validation Limits/)).toBeTruthy());
  });
});
