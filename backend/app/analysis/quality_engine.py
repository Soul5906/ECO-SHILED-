"""Data quality engine — computes quality score and detects structural issues."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.schemas.models import (
    ColumnQuality,
    QualityReport,
    Severity,
    ValidationIssue,
)


# ---------------------------------------------------------------------------
# Physical range defaults (overridable via settings)
# ---------------------------------------------------------------------------

DEFAULT_LIMITS: Dict[str, Dict[str, Optional[float]]] = {
    "power_kw":       {"min": 0.0, "max": 10_000.0},
    "irradiance_wm2": {"min": 0.0, "max": 1_500.0},
    "temperature_c":  {"min": -50.0, "max": 100.0},
    "voltage_v":      {"min": 0.0,  "max": 1_500.0},
    "current_a":      {"min": 0.0,  "max": 1_000.0},
    "frequency_hz":   {"min": 40.0, "max": 70.0},
    "humidity_pct":   {"min": 0.0,  "max": 100.0},
    "wind_speed_ms":  {"min": 0.0,  "max": 100.0},
}

REQUIRED_COLUMNS = ["timestamp", "power_kw", "irradiance_wm2", "temperature_c"]

COLUMN_ALIASES: Dict[str, str] = {
    "power": "power_kw",
    "pwr": "power_kw",
    "irradiance": "irradiance_wm2",
    "irrad": "irradiance_wm2",
    "ghi": "irradiance_wm2",
    "temp": "temperature_c",
    "temperature": "temperature_c",
    "t_amb": "temperature_c",
    "voltage": "voltage_v",
    "volt": "voltage_v",
    "current": "current_a",
    "amp": "current_a",
    "frequency": "frequency_hz",
    "freq": "frequency_hz",
    "energy": "energy_kwh",
    "humidity": "humidity_pct",
    "wind_speed": "wind_speed_ms",
    "time": "timestamp",
    "datetime": "timestamp",
    "ts": "timestamp",
}


def normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, List[str]]:
    """Rename columns using alias map; return df and list of transformations."""
    transformations: List[str] = []
    rename_map = {}
    for col in df.columns:
        lower = col.strip().lower()
        if lower in COLUMN_ALIASES and col != COLUMN_ALIASES[lower]:
            rename_map[col] = COLUMN_ALIASES[lower]
    if rename_map:
        df = df.rename(columns=rename_map)
        transformations.append(f"Renamed columns: {rename_map}")
    return df, transformations


def _make_issue(
    issue_type: str,
    severity: Severity,
    explanation: str,
    action: str,
    column: Optional[str] = None,
    indices: Optional[List[int]] = None,
) -> ValidationIssue:
    return ValidationIssue(
        issue_type=issue_type,
        column=column,
        row_indices=indices,
        severity=severity,
        explanation=explanation,
        suggested_action=action,
    )


def run_quality_engine(
    df: pd.DataFrame,
    settings: Optional[Dict[str, Any]] = None,
    expected_interval_minutes: float = 15.0,
) -> QualityReport:
    """Run the full data-quality pipeline and return a QualityReport."""
    issues: List[ValidationIssue] = []
    transformations: List[str] = []
    limits = DEFAULT_LIMITS.copy()

    if settings:
        pl = settings.get("physical_limits", {})
        if pl:
            for key in ["power_kw", "irradiance_wm2", "temperature_c", "voltage_v", "current_a"]:
                if key in limits:
                    if f"max_{key}" in pl:
                        limits[key]["max"] = pl[f"max_{key}"]
                    if f"min_{key}" in pl:
                        limits[key]["min"] = pl[f"min_{key}"]

    total_rows = len(df)

    # -----------------------------------------------------------------------
    # 1. Normalize columns
    # -----------------------------------------------------------------------
    df, tx = normalize_columns(df)
    transformations.extend(tx)

    # -----------------------------------------------------------------------
    # 2. Timestamp parsing
    # -----------------------------------------------------------------------
    valid_ts_count = 0
    invalid_ts_count = 0
    invalid_ts_indices: List[int] = []

    if "timestamp" in df.columns:
        original_ts = df["timestamp"].copy()
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            transformations.append("Parsed 'timestamp' column to UTC datetime.")
        except Exception:
            df["timestamp"] = pd.NaT
        nat_mask = df["timestamp"].isna()
        invalid_ts_count = int(nat_mask.sum())
        valid_ts_count = total_rows - invalid_ts_count
        invalid_ts_indices = list(df.index[nat_mask])
        if invalid_ts_count > 0:
            issues.append(_make_issue(
                "invalid_timestamp", Severity.HIGH,
                f"{invalid_ts_count} rows have unparseable timestamps.",
                "Inspect and correct the timestamp format. Rows are retained but excluded from time-based analysis.",
                column="timestamp", indices=invalid_ts_indices[:20],
            ))
    else:
        valid_ts_count = 0
        invalid_ts_count = total_rows
        issues.append(_make_issue(
            "missing_timestamp_column", Severity.CRITICAL,
            "No 'timestamp' column found.",
            "Ensure the CSV contains a column named 'timestamp' (or an alias like 'datetime', 'time', 'ts').",
        ))

    # -----------------------------------------------------------------------
    # 3. Duplicate timestamps
    # -----------------------------------------------------------------------
    dup_ts_count = 0
    dup_record_count = 0
    out_of_order_count = 0
    missing_periods = 0
    irregular_intervals = 0

    if "timestamp" in df.columns and valid_ts_count > 0:
        valid_df = df.dropna(subset=["timestamp"]).copy()

        dup_ts_mask = valid_df["timestamp"].duplicated(keep=False)
        dup_ts_count = int(dup_ts_mask.sum())
        if dup_ts_count > 0:
            dup_indices = list(valid_df.index[dup_ts_mask])[:20]
            issues.append(_make_issue(
                "duplicate_timestamps", Severity.MEDIUM,
                f"{dup_ts_count} rows share duplicate timestamps.",
                "Review and deduplicate rows with identical timestamps before time-series analysis.",
                column="timestamp", indices=dup_indices,
            ))

        dup_record_mask = valid_df.duplicated(keep=False)
        dup_record_count = int(dup_record_mask.sum())
        if dup_record_count > 0:
            issues.append(_make_issue(
                "duplicate_records", Severity.MEDIUM,
                f"{dup_record_count} fully duplicated rows detected.",
                "Remove duplicate rows before analysis.",
                indices=list(valid_df.index[dup_record_mask])[:20],
            ))

        sorted_ts = valid_df["timestamp"].sort_values()
        if not valid_df["timestamp"].is_monotonic_increasing:
            out_of_order_count = int((valid_df["timestamp"] != sorted_ts).sum())
            issues.append(_make_issue(
                "out_of_order_timestamps", Severity.LOW,
                f"{out_of_order_count} timestamps are out of chronological order.",
                "Sort the dataset by timestamp before uploading.",
                column="timestamp",
            ))
            transformations.append("Timestamps sorted to chronological order for analysis.")
            df = df.sort_values("timestamp").reset_index(drop=True)

        # Interval analysis
        ts_unique = sorted_ts.drop_duplicates()
        if len(ts_unique) > 2:
            deltas = ts_unique.diff().dropna().dt.total_seconds() / 60.0
            expected = expected_interval_minutes
            irregular_mask = (deltas - expected).abs() > expected * 0.5
            irregular_intervals = int(irregular_mask.sum())
            if irregular_intervals > 0:
                issues.append(_make_issue(
                    "irregular_sampling", Severity.LOW,
                    f"{irregular_intervals} intervals deviate >50% from expected {expected}-minute spacing.",
                    "Verify logger configuration. Irregular sampling may affect time-series analysis.",
                    column="timestamp",
                ))
            # Missing periods (gaps > 2x expected interval)
            large_gaps = deltas[deltas > expected * 2]
            missing_periods = int(len(large_gaps))
            if missing_periods > 0:
                issues.append(_make_issue(
                    "missing_time_periods", Severity.MEDIUM,
                    f"{missing_periods} gaps larger than 2× the expected interval ({expected} min).",
                    "Check for data-logger outages, communication failures, or missing file segments.",
                    column="timestamp",
                ))

    # -----------------------------------------------------------------------
    # 4. Missing required columns
    # -----------------------------------------------------------------------
    for req in REQUIRED_COLUMNS:
        if req == "timestamp":
            continue
        if req not in df.columns:
            issues.append(_make_issue(
                "missing_required_column", Severity.CRITICAL,
                f"Required column '{req}' is absent.",
                f"Ensure the CSV contains a column named '{req}' or a recognised alias.",
                column=req,
            ))

    # -----------------------------------------------------------------------
    # 5. Column-level quality
    # -----------------------------------------------------------------------
    numeric_cols = [c for c in df.columns if c != "timestamp" and pd.api.types.is_numeric_dtype(df[c])]
    column_quality: List[ColumnQuality] = []
    total_cells = max(total_rows * max(len(numeric_cols), 1), 1)
    missing_cells = 0

    for col in numeric_cols:
        series = df[col]
        missing = int(series.isna().sum())
        missing_pct = missing / total_rows * 100 if total_rows > 0 else 0.0
        missing_cells += missing

        # Negative checks
        neg_mask = series < 0
        neg_count = int(neg_mask.sum())
        if neg_count > 0 and col in ("power_kw", "irradiance_wm2"):
            issues.append(_make_issue(
                "negative_physical_value", Severity.MEDIUM,
                f"{neg_count} negative values in '{col}'.",
                f"Negative values in '{col}' are physically implausible. Investigate sensor or data-logger configuration.",
                column=col, indices=list(df.index[neg_mask])[:20],
            ))

        # Range checks
        range_violations = 0
        if col in limits:
            lo = limits[col].get("min")
            hi = limits[col].get("max")
            valid_series = series.dropna()
            range_mask = pd.Series(False, index=valid_series.index)
            if lo is not None:
                range_mask |= valid_series < lo
            if hi is not None:
                range_mask |= valid_series > hi
            range_violations = int(range_mask.sum())
            if range_violations > 0:
                issues.append(_make_issue(
                    "physical_range_violation", Severity.MEDIUM,
                    f"{range_violations} values in '{col}' outside physical limits [{lo}, {hi}].",
                    f"Review data for sensor miscalibration or data-entry errors in '{col}'.",
                    column=col,
                ))

        # Constant sensor
        is_constant = False
        valid_vals = series.dropna()
        if len(valid_vals) > 10:
            if valid_vals.std() < 1e-9:
                is_constant = True
                issues.append(_make_issue(
                    "constant_sensor", Severity.MEDIUM,
                    f"Column '{col}' shows zero variance — sensor may be stuck.",
                    "Inspect sensor hardware and communication channel.",
                    column=col,
                ))

        column_quality.append(ColumnQuality(
            column=col,
            missing_count=missing,
            missing_pct=round(missing_pct, 2),
            invalid_count=0,
            negative_count=neg_count,
            range_violations=range_violations,
            constant=is_constant,
            dtype=str(series.dtype),
        ))

    # -----------------------------------------------------------------------
    # 6. Completeness and quality score (heuristic)
    # -----------------------------------------------------------------------
    completeness_pct = 100.0 - (missing_cells / total_cells * 100) if total_cells else 0.0
    completeness_pct = round(max(0.0, min(100.0, completeness_pct)), 2)

    # Weighted heuristic (documented, not validated against a standard)
    penalty = 0.0
    penalty += min(40.0, invalid_ts_count / max(total_rows, 1) * 40.0)
    penalty += min(10.0, dup_ts_count / max(total_rows, 1) * 10.0)
    penalty += min(15.0, (100.0 - completeness_pct) * 0.15)
    penalty += min(10.0, missing_periods * 2.0)
    critical_issues = sum(1 for i in issues if i.severity == Severity.CRITICAL)
    high_issues = sum(1 for i in issues if i.severity == Severity.HIGH)
    penalty += critical_issues * 10.0
    penalty += high_issues * 5.0

    quality_score = round(max(0.0, min(100.0, 100.0 - penalty)), 1)

    return QualityReport(
        total_rows=total_rows,
        valid_timestamp_count=valid_ts_count,
        invalid_timestamp_count=invalid_ts_count,
        out_of_order_timestamps=out_of_order_count,
        duplicate_timestamps=dup_ts_count,
        duplicate_records=dup_record_count,
        missing_periods=missing_periods,
        irregular_intervals=irregular_intervals,
        column_quality=column_quality,
        quality_score=quality_score,
        quality_score_method=(
            "Heuristic score (0–100). Penalties applied for invalid timestamps (max -40), "
            "duplicate timestamps (-10), missing values (-15), missing time periods (-2 each), "
            "critical issues (-10 each), high-severity issues (-5 each). "
            "This score is a development heuristic and has not been validated against an industry standard."
        ),
        completeness_pct=completeness_pct,
        issues=issues,
        transformations_applied=transformations,
    )
