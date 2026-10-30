"""Analysis orchestration service — ties together all analysis modules."""
from __future__ import annotations

import io
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.analysis.anomaly_engine import run_anomaly_detectors
from app.analysis.diagnosis_engine import run_diagnosis
from app.analysis.quality_engine import normalize_columns, run_quality_engine
from app.analysis.scenarios import generate_scenario
from app.schemas.models import (
    AnalysisResult,
    AnalysisStatus,
    AnalysisSummary,
    AppSettings,
    DataSource,
    DatasetMetadata,
    DatasetValidationResponse,
    Severity,
    ValidationIssue,
)
from app.storage.database import (
    get_conn,
    get_analysis,
    get_dataset,
    list_analyses,
    save_analysis,
    save_dataset,
)

MAX_PREVIEW_ROWS = 20


# ---------------------------------------------------------------------------
# CSV ingestion helpers
# ---------------------------------------------------------------------------

def _parse_csv(content: bytes, filename: str = "upload.csv") -> Tuple[pd.DataFrame, List[str]]:
    """Parse CSV bytes; return DataFrame and list of parse warnings."""
    warnings: List[str] = []
    try:
        df = pd.read_csv(io.BytesIO(content), on_bad_lines="warn")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(io.BytesIO(content), encoding="latin-1", on_bad_lines="warn")
            warnings.append("File decoded as latin-1 (not UTF-8). Verify special characters.")
        except Exception as e:
            raise ValueError(f"Unable to parse CSV file: {e}") from e
    except Exception as e:
        raise ValueError(f"CSV parse error: {e}") from e

    if df.empty:
        raise ValueError("Uploaded file is empty or contains only headers.")

    # Strip whitespace from column names
    df.columns = [str(c).strip() for c in df.columns]

    # Detect and warn about duplicate column names
    if len(df.columns) != len(set(df.columns)):
        dupes = [c for c in df.columns if list(df.columns).count(c) > 1]
        warnings.append(f"Duplicate column names detected: {list(set(dupes))}. Analysis may be unreliable.")

    return df, warnings


def _detect_types(df: pd.DataFrame) -> Dict[str, str]:
    return {col: str(df[col].dtype) for col in df.columns}


def _safe_ts_range(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    if "timestamp" not in df.columns:
        return None, None
    ts = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    valid = ts.dropna()
    if valid.empty:
        return None, None
    return str(valid.min().isoformat()), str(valid.max().isoformat())


# ---------------------------------------------------------------------------
# Dataset validation
# ---------------------------------------------------------------------------

def validate_dataset(
    content: bytes,
    filename: str,
    settings: AppSettings,
) -> DatasetValidationResponse:
    """Validate uploaded CSV and return structured response. Does not persist."""
    issues: List[ValidationIssue] = []
    warnings: List[str] = []

    # File-size check
    if len(content) > settings.max_upload_size_bytes:
        raise ValueError(
            f"File size {len(content) / 1024 / 1024:.1f} MB exceeds limit of {settings.max_upload_size_mb} MB."
        )

    # File type check
    if not filename.lower().endswith(".csv"):
        issues.append(ValidationIssue(
            issue_type="unsupported_file_type",
            severity=Severity.CRITICAL,
            explanation=f"File '{filename}' does not have a .csv extension.",
            suggested_action="Upload a valid CSV file.",
        ))

    try:
        df, parse_warnings = _parse_csv(content, filename)
    except ValueError as e:
        return DatasetValidationResponse(
            valid=False,
            dataset_id="",
            row_count=0,
            column_names=[],
            issues=[ValidationIssue(
                issue_type="csv_parse_error",
                severity=Severity.CRITICAL,
                explanation=str(e),
                suggested_action="Check file format, encoding, and delimiter.",
            )],
            warnings=[],
            preview_rows=[],
        )

    warnings.extend(parse_warnings)

    # Row count check
    if len(df) > settings.max_rows:
        warnings.append(
            f"File has {len(df)} rows; only the first {settings.max_rows} will be analysed."
        )
        df = df.head(settings.max_rows)

    # Normalise columns
    df_norm, _ = normalize_columns(df.copy())
    col_names = list(df_norm.columns)

    # Required columns check
    for req in ["timestamp", "power_kw", "irradiance_wm2", "temperature_c"]:
        if req not in col_names:
            issues.append(ValidationIssue(
                issue_type="missing_required_column",
                column=req,
                severity=Severity.CRITICAL,
                explanation=f"Required column '{req}' (or a recognised alias) is absent.",
                suggested_action="Ensure the CSV includes a column matching the required name or alias.",
            ))

    dataset_id = str(uuid.uuid4())
    preview = df_norm.head(MAX_PREVIEW_ROWS).fillna("").to_dict(orient="records")
    valid = all(i.severity != Severity.CRITICAL for i in issues)

    return DatasetValidationResponse(
        valid=valid,
        dataset_id=dataset_id,
        row_count=len(df_norm),
        column_names=col_names,
        issues=issues,
        warnings=warnings,
        preview_rows=preview,
    )


# ---------------------------------------------------------------------------
# Dataset persistence
# ---------------------------------------------------------------------------

def persist_dataset(
    content: bytes,
    filename: str,
    source: DataSource,
    settings: AppSettings,
    scenario_id: Optional[str] = None,
) -> Tuple[str, pd.DataFrame]:
    """Parse, validate, and persist a dataset. Returns (dataset_id, DataFrame)."""
    df, _ = _parse_csv(content, filename)
    df, _ = normalize_columns(df)

    if len(df) > settings.max_rows:
        df = df.head(settings.max_rows)

    dataset_id = str(uuid.uuid4())
    ts_start, ts_end = _safe_ts_range(df)
    detected_types = _detect_types(df)

    # Store only public columns (strip _synthetic etc.)
    store_cols = [c for c in df.columns if not c.startswith("_")]
    data_json = df[store_cols].to_json(orient="records", date_format="iso")

    with get_conn() as conn:
        save_dataset(
            conn,
            dataset_id=dataset_id,
            filename=filename,
            source=source.value,
            row_count=len(df),
            column_names=list(df[store_cols].columns),
            detected_types=detected_types,
            ts_start=ts_start,
            ts_end=ts_end,
            file_size=len(content),
            scenario_id=scenario_id,
            data_json=data_json,
        )

    return dataset_id, df


def persist_scenario_dataset(scenario_id: str, settings: AppSettings) -> Tuple[str, pd.DataFrame]:
    """Generate, label, and persist a scenario dataset."""
    df = generate_scenario(scenario_id)
    csv_bytes = df.to_csv(index=False).encode()
    return persist_dataset(csv_bytes, f"{scenario_id}.csv", DataSource.DEMO, settings, scenario_id)


# ---------------------------------------------------------------------------
# Analysis runner
# ---------------------------------------------------------------------------

def run_analysis(
    dataset_id: str,
    settings: AppSettings,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> AnalysisResult:
    """Run the full analysis pipeline on a persisted dataset."""
    with get_conn() as conn:
        row = get_dataset(conn, dataset_id)

    if row is None:
        raise ValueError(f"Dataset '{dataset_id}' not found.")

    df = pd.read_json(io.StringIO(row["data_json"]), orient="records")
    # Restore proper types
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

    source_str = row["source"]
    source = DataSource(source_str) if source_str in [e.value for e in DataSource] else DataSource.UPLOAD

    # Merge settings with any overrides
    active_config: Dict[str, Any] = {
        "anomaly_thresholds": settings.anomaly_thresholds.model_dump(),
        "physical_limits": settings.physical_limits.model_dump(),
        "active_detectors": settings.active_detectors,
        "active_rules": settings.active_rules,
        "expected_interval_minutes": settings.expected_interval_minutes,
        "default_timezone": settings.default_timezone,
        "analysis_version": "1.0.0",
    }
    if config_overrides:
        active_config.update(config_overrides)

    # Run pipeline
    quality = run_quality_engine(
        df.copy(),
        settings=active_config,
        expected_interval_minutes=active_config.get("expected_interval_minutes", 15.0),
    )

    anomaly = run_anomaly_detectors(
        df.copy(),
        active_detectors=active_config.get("active_detectors"),
        thresholds=active_config.get("anomaly_thresholds", {}),
    )

    diagnosis, recommendations = run_diagnosis(
        df.copy(),
        quality=quality,
        anomaly=anomaly,
        active_rules=active_config.get("active_rules"),
    )

    warnings: List[str] = []
    limitations: List[str] = [
        "Diagnostic scores are heuristic values — not validated probabilities.",
        "No performance ratio, energy yield, or financial calculations are made without verified inputs.",
        "Physical inspection is required to confirm any hypothesis.",
        "This system does not recommend unsafe maintenance operations.",
    ]
    if quality.quality_score < 50.0:
        warnings.append(f"Data quality score is low ({quality.quality_score}/100). Analysis reliability is limited.")
    if quality.total_rows < 48:
        warnings.append("Dataset has fewer than 48 rows. Time-series detectors may not produce reliable results.")

    analysis_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    result = AnalysisResult(
        analysis_id=analysis_id,
        status=AnalysisStatus.COMPLETE,
        created_at=created_at,
        dataset_id=dataset_id,
        source=source,
        algorithm_version=active_config["analysis_version"],
        configuration_used=active_config,
        quality_report=quality,
        anomaly_summary=anomaly,
        diagnosis=diagnosis,
        recommendations=recommendations,
        warnings=warnings,
        limitations=limitations,
    )

    # Persist
    analysis_dict = result.model_dump(mode="json")
    analysis_dict["created_at"] = created_at.isoformat()
    with get_conn() as conn:
        save_analysis(conn, analysis_dict)

    return result


# ---------------------------------------------------------------------------
# Retrieval helpers
# ---------------------------------------------------------------------------

def get_analysis_result(analysis_id: str) -> Optional[AnalysisResult]:
    with get_conn() as conn:
        row = get_analysis(conn, analysis_id)
    if row is None:
        return None
    return _row_to_result(row)


def list_analysis_summaries(source: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[AnalysisSummary]:
    with get_conn() as conn:
        rows = list_analyses(conn, source=source, limit=limit, offset=offset)
    summaries = []
    for row in rows:
        quality = json.loads(row["quality_report_json"])
        anomaly = json.loads(row["anomaly_summary_json"])
        diagnosis = json.loads(row["diagnosis_json"])
        top_h = None
        if diagnosis.get("hypotheses"):
            h = min(diagnosis["hypotheses"], key=lambda h: h.get("rank", 999))
            top_h = h.get("name")
        summaries.append(AnalysisSummary(
            analysis_id=row["analysis_id"],
            status=AnalysisStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            dataset_id=row["dataset_id"],
            source=DataSource(row["source"]),
            quality_score=quality.get("quality_score", 0.0),
            anomaly_count=anomaly.get("total_anomalies", 0),
            top_hypothesis=top_h,
            row_count=quality.get("total_rows", 0),
        ))
    return summaries


def _row_to_result(row) -> AnalysisResult:
    return AnalysisResult(
        analysis_id=row["analysis_id"],
        status=AnalysisStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        dataset_id=row["dataset_id"],
        source=DataSource(row["source"]),
        algorithm_version=row["algorithm_version"],
        configuration_used=json.loads(row["configuration_json"]),
        quality_report=json.loads(row["quality_report_json"]),
        anomaly_summary=json.loads(row["anomaly_summary_json"]),
        diagnosis=json.loads(row["diagnosis_json"]),
        recommendations=json.loads(row["recommendations_json"]),
        warnings=json.loads(row["warnings_json"]),
        limitations=json.loads(row["limitations_json"]),
    )


def export_analysis_csv(analysis_id: str) -> Optional[str]:
    """Return CSV string of anomalies for an analysis."""
    result = get_analysis_result(analysis_id)
    if result is None:
        return None
    anomalies = result.anomaly_summary
    rows = []
    for a in anomalies.anomalies:
        rows.append({
            "anomaly_id": a.anomaly_id,
            "detector_name": a.detector_name,
            "detector_type": a.detector_type,
            "column": a.column,
            "timestamp": str(a.timestamp) if a.timestamp else "",
            "row_index": a.row_index,
            "measured_value": a.measured_value,
            "threshold_used": a.threshold_used,
            "severity": a.severity.value,
            "explanation": a.explanation,
        })
    if not rows:
        return "anomaly_id,detector_name,detector_type,column,timestamp,row_index,measured_value,threshold_used,severity,explanation\n"
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)
