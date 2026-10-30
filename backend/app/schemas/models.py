"""Pydantic schemas for ECO-SHIELD API."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, computed_field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    INFO = "info"


class DataSource(str, Enum):
    DEMO = "demo"
    UPLOAD = "upload"
    LIVE = "live"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    database: str


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

class ScenarioSummary(BaseModel):
    id: str
    name: str
    description: str
    tags: List[str]
    row_count: int
    duration_hours: float
    injected_conditions: List[str]


class ScenarioDetail(ScenarioSummary):
    purpose: str
    seed: int
    expected_anomaly_types: List[str]
    columns: List[str]


# ---------------------------------------------------------------------------
# Dataset / Telemetry
# ---------------------------------------------------------------------------

class DatasetMetadata(BaseModel):
    dataset_id: str
    filename: Optional[str] = None
    source: DataSource
    upload_time: datetime
    row_count: int
    column_names: List[str]
    detected_types: Dict[str, str]
    timestamp_range_start: Optional[datetime] = None
    timestamp_range_end: Optional[datetime] = None
    file_size_bytes: Optional[int] = None
    scenario_id: Optional[str] = None


class ValidationIssue(BaseModel):
    issue_type: str
    column: Optional[str] = None
    row_indices: Optional[List[int]] = None
    severity: Severity
    explanation: str
    suggested_action: str


class DatasetValidationResponse(BaseModel):
    valid: bool
    dataset_id: str
    row_count: int
    column_names: List[str]
    issues: List[ValidationIssue]
    warnings: List[str]
    preview_rows: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Data Quality
# ---------------------------------------------------------------------------

class ColumnQuality(BaseModel):
    column: str
    missing_count: int
    missing_pct: float
    invalid_count: int
    negative_count: int
    range_violations: int
    constant: bool
    dtype: str


class QualityReport(BaseModel):
    total_rows: int
    valid_timestamp_count: int
    invalid_timestamp_count: int
    out_of_order_timestamps: int
    duplicate_timestamps: int
    duplicate_records: int
    missing_periods: int
    irregular_intervals: int
    column_quality: List[ColumnQuality]
    quality_score: float
    quality_score_method: str
    completeness_pct: float
    issues: List[ValidationIssue]
    transformations_applied: List[str]


# ---------------------------------------------------------------------------
# Anomaly Detection
# ---------------------------------------------------------------------------

class AnomalyRecord(BaseModel):
    anomaly_id: str
    detector_name: str
    detector_type: str  # statistical | physical_rule
    column: Optional[str]
    timestamp: Optional[datetime]
    row_index: Optional[int]
    measured_value: Optional[float]
    threshold_used: Optional[float]
    severity: Severity
    explanation: str
    surrounding_context: Optional[Dict[str, Any]] = None
    original_value: Optional[float] = None


class AnomalySummary(BaseModel):
    total_anomalies: int
    by_severity: Dict[str, int]
    by_detector: Dict[str, int]
    detectors_run: List[str]
    anomalies: List[AnomalyRecord]


# ---------------------------------------------------------------------------
# Diagnosis / Root Cause
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    evidence_type: str  # observed_fact | derived_measurement | assumption
    description: str
    value: Optional[Any] = None
    unit: Optional[str] = None
    source_column: Optional[str] = None


class Hypothesis(BaseModel):
    hypothesis_id: str
    name: str
    rank: int
    score: float  # heuristic score, NOT a probability
    severity: Optional[str] = None
    supporting_evidence: List[EvidenceItem]
    contradicting_evidence: List[EvidenceItem]
    required_assumptions: List[str]
    missing_measurements: List[str]
    alternative_explanations: List[str]
    recommended_verification: str
    ranking_explanation: str
    triggered_rule_ids: List[str]
    input_features_used: List[str]


class DiagnosisReport(BaseModel):
    hypotheses: List[Hypothesis]
    uncertainty_note: str
    competing_causes_note: str
    insufficient_evidence: bool
    evidence_summary: Dict[str, Any]


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

class Recommendation(BaseModel):
    recommendation_id: str
    test_name: str
    reason: str
    hypotheses_addressed: List[str]
    evidence_required: List[str]
    expected_observation: str
    how_result_changes_diagnosis: str
    priority: str  # high | medium | low
    estimated_effort: Optional[str] = None
    safety_note: Optional[str] = None


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

class AnalysisRequest(BaseModel):
    dataset_id: str
    config_overrides: Optional[Dict[str, Any]] = None


class AnalysisResult(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    created_at: datetime
    dataset_id: str
    source: DataSource
    algorithm_version: str
    configuration_used: Dict[str, Any]
    quality_report: QualityReport
    anomaly_summary: AnomalySummary
    diagnosis: DiagnosisReport
    recommendations: List[Recommendation]
    warnings: List[str]
    limitations: List[str]


class AnalysisSummary(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    created_at: datetime
    dataset_id: str
    source: DataSource
    quality_score: float
    anomaly_count: int
    top_hypothesis: Optional[str] = None
    row_count: int


class CompareResponse(BaseModel):
    first_id: str
    second_id: str
    first_summary: AnalysisSummary
    second_summary: AnalysisSummary
    differences: Dict[str, Any]


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class AnomalyThresholds(BaseModel):
    mad_threshold: float = Field(default=3.5, ge=1.0, le=10.0)
    zscore_threshold: float = Field(default=3.0, ge=1.0, le=10.0)
    rate_of_change_threshold: float = Field(default=50.0, ge=0.0)
    gap_minutes: float = Field(default=30.0, ge=1.0)
    flatline_minutes: float = Field(default=60.0, ge=1.0)
    power_irradiance_drop_ratio: float = Field(default=0.5, ge=0.0, le=1.0)


class PhysicalLimits(BaseModel):
    max_power_kw: float = Field(default=10000.0, ge=0.0)
    max_irradiance_wm2: float = Field(default=1500.0, ge=0.0)
    min_temperature_c: float = Field(default=-50.0)
    max_temperature_c: float = Field(default=100.0)
    max_voltage_v: float = Field(default=1500.0, ge=0.0)
    max_current_a: float = Field(default=1000.0, ge=0.0)


class AppSettings(BaseModel):
    anomaly_thresholds: AnomalyThresholds = Field(default_factory=AnomalyThresholds)
    physical_limits: PhysicalLimits = Field(default_factory=PhysicalLimits)
    default_timezone: str = "UTC"
    expected_interval_minutes: float = Field(default=15.0, ge=1.0)
    max_upload_size_mb: int = Field(default=50, ge=1, le=500)
    max_rows: int = Field(default=100000, ge=100)
    active_detectors: List[str] = Field(
        default=[
            "mad_outlier",
            "zscore_outlier",
            "rate_of_change",
            "missing_gaps",
            "flatline",
            "duplicate_timestamps",
            "power_irradiance_drop",
            "temperature_anomaly",
            "sensor_drift",
            "periodic_pattern",
        ]
    )
    active_rules: List[str] = Field(
        default=[
            "telemetry_failure",
            "sensor_drift",
            "reduced_resource",
            "shading_soiling",
            "module_performance",
            "inverter_electrical",
            "temperature_issue",
            "unexpected_decline",
            "insufficient_evidence",
        ]
    )
    report_retention_days: int = Field(default=90, ge=0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def max_upload_size_bytes(self) -> int:
        """Derived byte limit for file-size checks in route handlers."""
        return self.max_upload_size_mb * 1024 * 1024


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    field: Optional[str] = None
