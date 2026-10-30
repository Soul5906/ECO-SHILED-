// Shared TypeScript types for ECO-SHIELD frontend

export type Severity = 'low' | 'medium' | 'high' | 'critical' | 'info';
export type DataSource = 'demo' | 'upload' | 'live';
export type AnalysisStatus = 'pending' | 'running' | 'complete' | 'failed';

// Health
export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  database: string;
}

// Scenarios
export interface ScenarioSummary {
  id: string;
  name: string;
  description: string;
  tags: string[];
  row_count: number;
  duration_hours: number;
  injected_conditions: string[];
}

export interface ScenarioDetail extends ScenarioSummary {
  purpose: string;
  seed: number;
  expected_anomaly_types: string[];
  columns: string[];
}

// Validation
export interface ValidationIssue {
  issue_type: string;
  column?: string;
  row_indices?: number[];
  severity: Severity;
  explanation: string;
  suggested_action: string;
}

export interface DatasetValidationResponse {
  valid: boolean;
  dataset_id: string;
  row_count: number;
  column_names: string[];
  issues: ValidationIssue[];
  warnings: string[];
  preview_rows: Record<string, unknown>[];
}

// Quality
export interface ColumnQuality {
  column: string;
  missing_count: number;
  missing_pct: number;
  invalid_count: number;
  negative_count: number;
  range_violations: number;
  constant: boolean;
  dtype: string;
}

export interface QualityReport {
  total_rows: number;
  valid_timestamp_count: number;
  invalid_timestamp_count: number;
  out_of_order_timestamps: number;
  duplicate_timestamps: number;
  duplicate_records: number;
  missing_periods: number;
  irregular_intervals: number;
  column_quality: ColumnQuality[];
  quality_score: number;
  quality_score_method: string;
  completeness_pct: number;
  issues: ValidationIssue[];
  transformations_applied: string[];
}

// Anomaly
export interface AnomalyRecord {
  anomaly_id: string;
  detector_name: string;
  detector_type: string;
  column?: string;
  timestamp?: string;
  row_index?: number;
  measured_value?: number;
  threshold_used?: number;
  severity: Severity;
  explanation: string;
  surrounding_context?: Record<string, unknown>;
  original_value?: number;
}

export interface AnomalySummary {
  total_anomalies: number;
  by_severity: Record<string, number>;
  by_detector: Record<string, number>;
  detectors_run: string[];
  anomalies: AnomalyRecord[];
}

// Diagnosis
export interface EvidenceItem {
  evidence_type: string;
  description: string;
  value?: unknown;
  unit?: string;
  source_column?: string;
}

export interface Hypothesis {
  hypothesis_id: string;
  name: string;
  rank: number;
  score: number;
  severity?: string;
  supporting_evidence: EvidenceItem[];
  contradicting_evidence: EvidenceItem[];
  required_assumptions: string[];
  missing_measurements: string[];
  alternative_explanations: string[];
  recommended_verification: string;
  ranking_explanation: string;
  triggered_rule_ids: string[];
  input_features_used: string[];
}

export interface DiagnosisReport {
  hypotheses: Hypothesis[];
  uncertainty_note: string;
  competing_causes_note: string;
  insufficient_evidence: boolean;
  evidence_summary: Record<string, unknown>;
}

// Recommendations
export interface Recommendation {
  recommendation_id: string;
  test_name: string;
  reason: string;
  hypotheses_addressed: string[];
  evidence_required: string[];
  expected_observation: string;
  how_result_changes_diagnosis: string;
  priority: string;
  estimated_effort?: string;
  safety_note?: string;
}

// Analysis
export interface AnalysisResult {
  analysis_id: string;
  status: AnalysisStatus;
  created_at: string;
  dataset_id: string;
  source: DataSource;
  algorithm_version: string;
  configuration_used: Record<string, unknown>;
  quality_report: QualityReport;
  anomaly_summary: AnomalySummary;
  diagnosis: DiagnosisReport;
  recommendations: Recommendation[];
  warnings: string[];
  limitations: string[];
}

export interface AnalysisSummary {
  analysis_id: string;
  status: AnalysisStatus;
  created_at: string;
  dataset_id: string;
  source: DataSource;
  quality_score: number;
  anomaly_count: number;
  top_hypothesis?: string;
  row_count: number;
}

export interface CompareResponse {
  first_id: string;
  second_id: string;
  first_summary: AnalysisSummary;
  second_summary: AnalysisSummary;
  differences: Record<string, unknown>;
}

// Settings
export interface AnomalyThresholds {
  mad_threshold: number;
  zscore_threshold: number;
  rate_of_change_threshold: number;
  gap_minutes: number;
  flatline_minutes: number;
  power_irradiance_drop_ratio: number;
}

export interface PhysicalLimits {
  max_power_kw: number;
  max_irradiance_wm2: number;
  min_temperature_c: number;
  max_temperature_c: number;
  max_voltage_v: number;
  max_current_a: number;
}

export interface AppSettings {
  anomaly_thresholds: AnomalyThresholds;
  physical_limits: PhysicalLimits;
  default_timezone: string;
  expected_interval_minutes: number;
  max_upload_size_mb: number;
  max_rows: number;
  active_detectors: string[];
  active_rules: string[];
  report_retention_days: number;
}

// API error
export interface ApiError {
  error: string;
  detail?: string;
  field?: string;
}
