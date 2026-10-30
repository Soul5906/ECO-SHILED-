"""Anomaly detection engine — modular detectors for solar telemetry."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.schemas.models import AnomalyRecord, AnomalySummary, Severity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return str(uuid.uuid4())


def _ts(row: pd.Series) -> Optional[datetime]:
    ts = row.get("timestamp")
    if pd.isna(ts):
        return None
    if hasattr(ts, "to_pydatetime"):
        return ts.to_pydatetime()
    return ts


def _context(df: pd.DataFrame, idx: int, window: int = 3) -> Dict[str, Any]:
    lo = max(0, idx - window)
    hi = min(len(df), idx + window + 1)
    return df.iloc[lo:hi][
        [c for c in ["timestamp", "power_kw", "irradiance_wm2", "temperature_c"] if c in df.columns]
    ].to_dict(orient="list")


# ---------------------------------------------------------------------------
# Individual Detectors
# ---------------------------------------------------------------------------

def detect_mad_outliers(
    df: pd.DataFrame,
    threshold: float = 3.5,
    columns: Optional[List[str]] = None,
) -> List[AnomalyRecord]:
    """Robust statistical outlier detection via Median Absolute Deviation."""
    records: List[AnomalyRecord] = []
    cols = columns or ["power_kw", "irradiance_wm2", "temperature_c"]
    for col in cols:
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if len(series) < 5:
            continue
        median = series.median()
        mad = (series - median).abs().median()
        if mad < 1e-9:
            continue  # zero variance — handled by flatline detector
        modified_z = 0.6745 * (series - median) / mad
        outlier_mask = modified_z.abs() > threshold
        for idx in series[outlier_mask].index:
            row = df.loc[idx]
            records.append(AnomalyRecord(
                anomaly_id=_uid(),
                detector_name="mad_outlier",
                detector_type="statistical",
                column=col,
                timestamp=_ts(row),
                row_index=int(idx),
                measured_value=float(row[col]),
                threshold_used=threshold,
                severity=Severity.MEDIUM if modified_z.abs().loc[idx] < threshold * 1.5 else Severity.HIGH,
                explanation=(
                    f"MAD-based modified Z-score {modified_z.abs().loc[idx]:.2f} exceeds threshold {threshold} "
                    f"for '{col}'. Value: {row[col]:.4g}, median: {median:.4g}."
                ),
                surrounding_context=_context(df, int(df.index.get_loc(idx))),
                original_value=float(row[col]),
            ))
    return records


def detect_zscore_outliers(
    df: pd.DataFrame,
    threshold: float = 3.0,
    columns: Optional[List[str]] = None,
) -> List[AnomalyRecord]:
    """Z-score outlier detection (appropriate only for roughly normal series)."""
    records: List[AnomalyRecord] = []
    cols = columns or ["power_kw", "irradiance_wm2", "temperature_c"]
    for col in cols:
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if len(series) < 30:
            continue
        mean, std = series.mean(), series.std()
        if std < 1e-9:
            continue
        z = (series - mean) / std
        for idx in series[z.abs() > threshold].index:
            row = df.loc[idx]
            records.append(AnomalyRecord(
                anomaly_id=_uid(),
                detector_name="zscore_outlier",
                detector_type="statistical",
                column=col,
                timestamp=_ts(row),
                row_index=int(idx),
                measured_value=float(row[col]),
                threshold_used=threshold,
                severity=Severity.LOW,
                explanation=(
                    f"Z-score {z.loc[idx]:.2f} exceeds threshold {threshold} for '{col}'. "
                    f"Note: Z-score assumes approximate normality; treat this as supplementary to MAD results."
                ),
                surrounding_context=_context(df, int(df.index.get_loc(idx))),
                original_value=float(row[col]),
            ))
    return records


def detect_rate_of_change(
    df: pd.DataFrame,
    threshold: float = 50.0,
    columns: Optional[List[str]] = None,
) -> List[AnomalyRecord]:
    """Detect sudden step changes (rate-of-change spikes)."""
    records: List[AnomalyRecord] = []
    if "timestamp" not in df.columns:
        return records
    work = df.dropna(subset=["timestamp"]).sort_values("timestamp").copy()
    cols = columns or ["power_kw", "irradiance_wm2"]
    for col in cols:
        if col not in work.columns:
            continue
        series = work[col].dropna()
        if len(series) < 3:
            continue
        delta = series.diff().abs()
        for idx in delta[delta > threshold].index:
            pos = int(work.index.get_loc(idx))
            row = work.loc[idx]
            records.append(AnomalyRecord(
                anomaly_id=_uid(),
                detector_name="rate_of_change",
                detector_type="statistical",
                column=col,
                timestamp=_ts(row),
                row_index=int(idx),
                measured_value=float(delta.loc[idx]),
                threshold_used=threshold,
                severity=Severity.MEDIUM,
                explanation=(
                    f"Sudden change of {delta.loc[idx]:.2f} in '{col}' between consecutive readings "
                    f"exceeds threshold of {threshold}."
                ),
                surrounding_context=_context(work, pos),
                original_value=float(row[col]) if not pd.isna(row[col]) else None,
            ))
    return records


def detect_missing_gaps(
    df: pd.DataFrame,
    expected_interval_minutes: float = 15.0,
    gap_multiplier: float = 3.0,
) -> List[AnomalyRecord]:
    """Detect gaps larger than gap_multiplier × expected interval."""
    records: List[AnomalyRecord] = []
    if "timestamp" not in df.columns:
        return records
    work = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    if len(work) < 2:
        return records
    deltas = work["timestamp"].diff().dt.total_seconds() / 60.0
    threshold = expected_interval_minutes * gap_multiplier
    for idx in deltas[deltas > threshold].index:
        pos = int(work.index.get_loc(idx))
        row = work.loc[idx]
        gap_min = float(deltas.loc[idx])
        records.append(AnomalyRecord(
            anomaly_id=_uid(),
            detector_name="missing_gaps",
            detector_type="physical_rule",
            column="timestamp",
            timestamp=_ts(row),
            row_index=int(idx),
            measured_value=gap_min,
            threshold_used=threshold,
            severity=Severity.MEDIUM if gap_min < threshold * 5 else Severity.HIGH,
            explanation=(
                f"Data gap of {gap_min:.1f} min at this timestamp, exceeding {threshold:.1f}-min threshold "
                f"({gap_multiplier}× the expected {expected_interval_minutes}-min interval)."
            ),
            surrounding_context=_context(work, pos),
        ))
    return records


def detect_flatline(
    df: pd.DataFrame,
    window: int = 10,
    columns: Optional[List[str]] = None,
) -> List[AnomalyRecord]:
    """Detect stuck/flatlined sensors by looking for zero-variance rolling windows."""
    records: List[AnomalyRecord] = []
    cols = columns or ["power_kw", "irradiance_wm2", "temperature_c"]
    for col in cols:
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if len(series) < window + 2:
            continue
        roll_std = series.rolling(window).std()
        flatline_starts = roll_std[roll_std < 1e-9].index
        if len(flatline_starts) == 0:
            continue
        # Group consecutive flatline indices
        reported: set = set()
        for idx in flatline_starts:
            if idx in reported:
                continue
            pos = int(series.index.get_loc(idx))
            row = df.loc[idx]
            records.append(AnomalyRecord(
                anomaly_id=_uid(),
                detector_name="flatline",
                detector_type="physical_rule",
                column=col,
                timestamp=_ts(row),
                row_index=int(idx),
                measured_value=float(series.loc[idx]),
                threshold_used=float(window),
                severity=Severity.MEDIUM,
                explanation=(
                    f"Column '{col}' shows zero variance over a {window}-reading window ending here — "
                    f"possible stuck or failed sensor."
                ),
                surrounding_context=_context(df, pos),
                original_value=float(series.loc[idx]),
            ))
            reported.add(idx)
    return records


def detect_duplicate_timestamps(df: pd.DataFrame) -> List[AnomalyRecord]:
    """Flag rows with duplicated timestamps."""
    records: List[AnomalyRecord] = []
    if "timestamp" not in df.columns:
        return records
    work = df.dropna(subset=["timestamp"])
    dup_mask = work["timestamp"].duplicated(keep="first")
    for idx in work[dup_mask].index:
        row = work.loc[idx]
        records.append(AnomalyRecord(
            anomaly_id=_uid(),
            detector_name="duplicate_timestamps",
            detector_type="physical_rule",
            column="timestamp",
            timestamp=_ts(row),
            row_index=int(idx),
            measured_value=None,
            threshold_used=None,
            severity=Severity.LOW,
            explanation=f"Timestamp {row.get('timestamp')} appears more than once.",
            surrounding_context=None,
        ))
    return records


def detect_power_irradiance_drop(
    df: pd.DataFrame,
    drop_ratio_threshold: float = 0.5,
) -> List[AnomalyRecord]:
    """Detect power drops disproportionate to available irradiance."""
    records: List[AnomalyRecord] = []
    if not {"power_kw", "irradiance_wm2"}.issubset(df.columns):
        return records

    work = df[["timestamp", "power_kw", "irradiance_wm2"]].dropna().copy()
    if len(work) < 20:
        return records

    # Normalise both to [0,1] range for comparison
    max_p = work["power_kw"].max()
    max_i = work["irradiance_wm2"].max()
    if max_p < 1e-6 or max_i < 1e-6:
        return records

    work["norm_p"] = work["power_kw"] / max_p
    work["norm_i"] = work["irradiance_wm2"] / max_i

    # Only flag rows where irradiance is meaningful (>10% of max)
    active = work[work["norm_i"] > 0.1].copy()
    if len(active) < 5:
        return records

    active["ratio"] = active["norm_p"] / active["norm_i"]
    median_ratio = active["ratio"].median()

    for idx, row_data in active[active["ratio"] < drop_ratio_threshold * median_ratio].iterrows():
        pos = int(df.index.get_loc(idx)) if idx in df.index else 0
        records.append(AnomalyRecord(
            anomaly_id=_uid(),
            detector_name="power_irradiance_drop",
            detector_type="physical_rule",
            column="power_kw",
            timestamp=row_data.get("timestamp") if not pd.isna(row_data.get("timestamp")) else None,
            row_index=int(idx),
            measured_value=float(row_data["ratio"]),
            threshold_used=float(drop_ratio_threshold * median_ratio),
            severity=Severity.HIGH,
            explanation=(
                f"Power-to-irradiance ratio ({row_data['ratio']:.2f}) is "
                f"{drop_ratio_threshold * 100:.0f}% below expected ratio ({median_ratio:.2f}) "
                f"for available irradiance. May indicate shading, soiling, or inverter issue."
            ),
            surrounding_context=_context(df, pos),
        ))
    return records


def detect_temperature_anomaly(
    df: pd.DataFrame,
    min_c: float = -50.0,
    max_c: float = 100.0,
) -> List[AnomalyRecord]:
    records: List[AnomalyRecord] = []
    if "temperature_c" not in df.columns:
        return records
    series = df["temperature_c"].dropna()
    for idx in series[(series < min_c) | (series > max_c)].index:
        row = df.loc[idx]
        pos = int(df.index.get_loc(idx))
        records.append(AnomalyRecord(
            anomaly_id=_uid(),
            detector_name="temperature_anomaly",
            detector_type="physical_rule",
            column="temperature_c",
            timestamp=_ts(row),
            row_index=int(idx),
            measured_value=float(series.loc[idx]),
            threshold_used=None,
            severity=Severity.MEDIUM,
            explanation=(
                f"Temperature {series.loc[idx]:.1f}°C is outside the expected physical range [{min_c}, {max_c}]."
            ),
            surrounding_context=_context(df, pos),
            original_value=float(series.loc[idx]),
        ))
    return records


def detect_sensor_drift(
    df: pd.DataFrame,
    window_frac: float = 0.1,
    drift_threshold: float = 0.3,
) -> List[AnomalyRecord]:
    """Detect gradual sensor drift by comparing rolling means."""
    records: List[AnomalyRecord] = []
    cols = ["irradiance_wm2", "temperature_c"]
    for col in cols:
        if col not in df.columns:
            continue
        series = df[col].dropna()
        n = len(series)
        if n < 50:
            continue
        w = max(10, int(n * window_frac))
        rolling = series.rolling(w).mean()
        overall_mean = series.mean()
        if abs(overall_mean) < 1e-6:
            continue
        relative_drift = (rolling - overall_mean).abs() / abs(overall_mean)
        drift_points = relative_drift[relative_drift > drift_threshold]
        if len(drift_points) > 0 and len(drift_points) / n > 0.15:
            idx = drift_points.index[0]
            row = df.loc[idx]
            records.append(AnomalyRecord(
                anomaly_id=_uid(),
                detector_name="sensor_drift",
                detector_type="statistical",
                column=col,
                timestamp=_ts(row),
                row_index=int(idx),
                measured_value=float(drift_points.iloc[0]),
                threshold_used=drift_threshold,
                severity=Severity.MEDIUM,
                explanation=(
                    f"Rolling mean of '{col}' deviates >30% from overall mean in "
                    f"{len(drift_points)} readings, suggesting possible sensor drift or offset."
                ),
                surrounding_context=None,
            ))
    return records


def detect_periodic_patterns(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
) -> List[AnomalyRecord]:
    """Detect repeated abnormal periodic patterns using autocorrelation hints."""
    records: List[AnomalyRecord] = []
    cols = columns or ["power_kw"]
    for col in cols:
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if len(series) < 96:  # need at least 4 days of 15-min data
            continue
        # Look for repeated zeros in daytime (irradiance > 0)
        if "irradiance_wm2" in df.columns:
            irr = df.loc[series.index, "irradiance_wm2"].fillna(0)
            daytime = series[irr > 50]
            if len(daytime) < 20:
                continue
            zero_frac = (daytime < 0.01).mean()
            if zero_frac > 0.1:
                records.append(AnomalyRecord(
                    anomaly_id=_uid(),
                    detector_name="periodic_pattern",
                    detector_type="statistical",
                    column=col,
                    timestamp=None,
                    row_index=None,
                    measured_value=round(float(zero_frac * 100), 2),
                    threshold_used=10.0,
                    severity=Severity.MEDIUM,
                    explanation=(
                        f"{zero_frac * 100:.1f}% of daytime readings show near-zero power despite available irradiance, "
                        f"suggesting a recurring fault pattern (e.g., repeated inverter trips)."
                    ),
                    surrounding_context=None,
                ))
    return records


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

DETECTOR_REGISTRY = {
    "mad_outlier": detect_mad_outliers,
    "zscore_outlier": detect_zscore_outliers,
    "rate_of_change": detect_rate_of_change,
    "missing_gaps": detect_missing_gaps,
    "flatline": detect_flatline,
    "duplicate_timestamps": detect_duplicate_timestamps,
    "power_irradiance_drop": detect_power_irradiance_drop,
    "temperature_anomaly": detect_temperature_anomaly,
    "sensor_drift": detect_sensor_drift,
    "periodic_pattern": detect_periodic_patterns,
}


def run_anomaly_detectors(
    df: pd.DataFrame,
    active_detectors: Optional[List[str]] = None,
    thresholds: Optional[Dict[str, Any]] = None,
) -> AnomalySummary:
    """Run all active anomaly detectors and aggregate results."""
    th = thresholds or {}
    enabled = active_detectors or list(DETECTOR_REGISTRY.keys())
    all_anomalies: List[AnomalyRecord] = []
    detectors_run: List[str] = []

    for name in enabled:
        fn = DETECTOR_REGISTRY.get(name)
        if fn is None:
            continue
        detectors_run.append(name)
        try:
            kwargs: Dict[str, Any] = {}
            if name == "mad_outlier" and "mad_threshold" in th:
                kwargs["threshold"] = th["mad_threshold"]
            elif name == "zscore_outlier" and "zscore_threshold" in th:
                kwargs["threshold"] = th["zscore_threshold"]
            elif name == "rate_of_change" and "rate_of_change_threshold" in th:
                kwargs["threshold"] = th["rate_of_change_threshold"]
            elif name == "missing_gaps" and "gap_minutes" in th:
                kwargs["expected_interval_minutes"] = th.get("gap_minutes", 15.0)
            elif name == "flatline" and "flatline_minutes" in th:
                # approximate window from minutes (assume 15-min intervals)
                interval = th.get("expected_interval_minutes", 15.0)
                kwargs["window"] = max(3, int(th["flatline_minutes"] / interval))
            elif name == "power_irradiance_drop" and "power_irradiance_drop_ratio" in th:
                kwargs["drop_ratio_threshold"] = th["power_irradiance_drop_ratio"]

            result = fn(df, **kwargs)
            all_anomalies.extend(result)
        except Exception as exc:
            # Never crash — log and continue
            all_anomalies.append(AnomalyRecord(
                anomaly_id=_uid(),
                detector_name=name,
                detector_type="detector_error",
                column=None,
                timestamp=None,
                row_index=None,
                measured_value=None,
                threshold_used=None,
                severity=Severity.INFO,
                explanation=f"Detector '{name}' encountered an error and could not complete: {exc!s}",
            ))

    by_severity: Dict[str, int] = {}
    by_detector: Dict[str, int] = {}
    for a in all_anomalies:
        by_severity[a.severity.value] = by_severity.get(a.severity.value, 0) + 1
        by_detector[a.detector_name] = by_detector.get(a.detector_name, 0) + 1

    return AnomalySummary(
        total_anomalies=len(all_anomalies),
        by_severity=by_severity,
        by_detector=by_detector,
        detectors_run=detectors_run,
        anomalies=all_anomalies,
    )
