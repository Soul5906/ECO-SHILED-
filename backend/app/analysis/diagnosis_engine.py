"""Root-cause diagnosis engine — explainable rule-based hypotheses."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.schemas.models import (
    AnomalySummary,
    DiagnosisReport,
    EvidenceItem,
    Hypothesis,
    QualityReport,
    Recommendation,
)


def _uid() -> str:
    return str(uuid.uuid4())


def _fact(desc: str, value: Any = None, unit: Optional[str] = None, col: Optional[str] = None) -> EvidenceItem:
    return EvidenceItem(evidence_type="observed_fact", description=desc, value=value, unit=unit, source_column=col)


def _derived(desc: str, value: Any = None, unit: Optional[str] = None) -> EvidenceItem:
    return EvidenceItem(evidence_type="derived_measurement", description=desc, value=value, unit=unit)


def _assumption(desc: str) -> EvidenceItem:
    return EvidenceItem(evidence_type="assumption", description=desc)


# ---------------------------------------------------------------------------
# Rule implementations
# ---------------------------------------------------------------------------

def rule_telemetry_failure(
    df: pd.DataFrame,
    quality: QualityReport,
    anomaly: AnomalySummary,
) -> Optional[Hypothesis]:
    """RULE-001: Data or communication failure."""
    score = 0.0
    supporting: List[EvidenceItem] = []
    contradicting: List[EvidenceItem] = []
    missing: List[str] = []
    assumptions: List[str] = []

    gap_count = sum(1 for a in anomaly.anomalies if a.detector_name == "missing_gaps")
    dup_ts = quality.duplicate_timestamps
    invalid_ts = quality.invalid_timestamp_count
    completeness = quality.completeness_pct

    if gap_count > 0:
        score += min(25.0, gap_count * 5.0)
        supporting.append(_fact(f"{gap_count} data gaps detected exceeding expected interval", gap_count))

    if invalid_ts > 0:
        score += min(20.0, invalid_ts / max(quality.total_rows, 1) * 100.0)
        supporting.append(_fact(f"{invalid_ts} rows with invalid or unparseable timestamps", invalid_ts))

    if dup_ts > 0:
        score += min(10.0, dup_ts * 2.0)
        supporting.append(_fact(f"{dup_ts} duplicate timestamps", dup_ts))

    if completeness < 70.0:
        score += 15.0
        supporting.append(_derived(f"Data completeness {completeness:.1f}% is low", completeness, "%"))

    if "status" not in df.columns:
        missing.append("inverter/logger status field")

    if score < 5.0:
        contradicting.append(_fact("Data gaps and timestamp issues are within acceptable limits."))

    if score < 5.0:
        return None

    return Hypothesis(
        hypothesis_id=_uid(),
        name="Telemetry / Communication Failure",
        rank=0,
        score=round(score, 2),
        severity="operational",
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        required_assumptions=["Data gaps are not caused by intentional downtime windows."],
        missing_measurements=missing,
        alternative_explanations=["Intentional maintenance window", "Site shutdown"],
        recommended_verification="Check logger connectivity logs and communication interface status.",
        ranking_explanation="Ranked by count of timestamp and data-gap issues.",
        triggered_rule_ids=["RULE-001"],
        input_features_used=["timestamp", "completeness"],
    )


def rule_sensor_drift(
    df: pd.DataFrame,
    quality: QualityReport,
    anomaly: AnomalySummary,
) -> Optional[Hypothesis]:
    """RULE-002: Irradiance sensor drift or failure."""
    score = 0.0
    supporting: List[EvidenceItem] = []
    contradicting: List[EvidenceItem] = []
    missing: List[str] = []

    drift_count = sum(1 for a in anomaly.anomalies if a.detector_name == "sensor_drift")
    flatline_irr = sum(1 for a in anomaly.anomalies if a.detector_name == "flatline" and a.column == "irradiance_wm2")
    const_irr = any(c.constant for c in quality.column_quality if c.column == "irradiance_wm2")

    if drift_count > 0:
        score += 30.0
        supporting.append(_fact("Sensor drift indicators detected in irradiance channel", drift_count))

    if flatline_irr > 0:
        score += 25.0
        supporting.append(_fact(f"{flatline_irr} flatline periods in irradiance_wm2", flatline_irr))

    if const_irr:
        score += 20.0
        supporting.append(_fact("Irradiance sensor reads constant value — possibly stuck or disconnected"))

    if "irradiance_wm2" not in df.columns:
        missing.append("irradiance_wm2 (primary signal for this hypothesis)")
        score = max(score, 5.0)

    if score < 5.0:
        contradicting.append(_fact("No sensor drift or flatline indicators present in irradiance channel."))
        return None

    missing.append("Reference pyranometer reading for cross-validation")
    missing.append("Sensor calibration certificate date")

    return Hypothesis(
        hypothesis_id=_uid(),
        name="Irradiance Sensor Drift or Failure",
        rank=0,
        score=round(score, 2),
        severity="operational",
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        required_assumptions=["Irradiance sensor is the primary measurement, not a peer reference."],
        missing_measurements=missing,
        alternative_explanations=["Overcast sky causing genuinely low irradiance", "Night-time data"],
        recommended_verification="Compare irradiance readings with a co-located calibrated reference sensor or NWP model estimate.",
        ranking_explanation="Ranked by presence of drift indicators and flatline anomalies in irradiance channel.",
        triggered_rule_ids=["RULE-002"],
        input_features_used=["irradiance_wm2"],
    )


def rule_reduced_resource(
    df: pd.DataFrame,
    quality: QualityReport,
    anomaly: AnomalySummary,
) -> Optional[Hypothesis]:
    """RULE-003: Reduced solar resource / cloud passage."""
    score = 0.0
    supporting: List[EvidenceItem] = []
    contradicting: List[EvidenceItem] = []
    missing: List[str] = []

    if "irradiance_wm2" not in df.columns or "power_kw" not in df.columns:
        return None

    valid = df[["irradiance_wm2", "power_kw"]].dropna()
    if len(valid) < 20:
        return None

    irr_cv = valid["irradiance_wm2"].std() / (valid["irradiance_wm2"].mean() + 1e-6)
    pow_cv = valid["power_kw"].std() / (valid["power_kw"].mean() + 1e-6)

    if irr_cv > 0.4:
        score += 20.0
        supporting.append(_derived(f"Irradiance variability (CV={irr_cv:.2f}) is high, consistent with cloud passage", round(irr_cv, 3)))

    # Power and irradiance tracking
    corr = valid["power_kw"].corr(valid["irradiance_wm2"])
    if corr > 0.7:
        score += 15.0
        supporting.append(_derived(f"Power tracks irradiance closely (correlation {corr:.2f})", round(corr, 2)))
        contradicting.append(_fact("Close power-irradiance tracking suggests no inverter-level fault."))

    if irr_cv < 0.2 and pow_cv > 0.4:
        score = max(0.0, score - 10.0)
        contradicting.append(_derived("Irradiance is stable but power varies — suggests system fault rather than resource reduction."))

    if score < 10.0:
        return None

    missing.append("NWP or satellite irradiance reference for independent validation")

    return Hypothesis(
        hypothesis_id=_uid(),
        name="Reduced Solar Resource / Cloud Passage",
        rank=0,
        score=round(score, 2),
        severity="informational",
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        required_assumptions=["Irradiance sensor reading is approximately accurate."],
        missing_measurements=missing,
        alternative_explanations=["Sensor drift causing apparent irradiance drop", "Dust accumulation"],
        recommended_verification="Compare irradiance with NWP model output or adjacent reference station.",
        ranking_explanation="Ranked by irradiance variability and power-irradiance correlation.",
        triggered_rule_ids=["RULE-003"],
        input_features_used=["irradiance_wm2", "power_kw"],
    )


def rule_shading_soiling(
    df: pd.DataFrame,
    quality: QualityReport,
    anomaly: AnomalySummary,
) -> Optional[Hypothesis]:
    """RULE-004: Possible shading or soiling."""
    score = 0.0
    supporting: List[EvidenceItem] = []
    contradicting: List[EvidenceItem] = []
    missing: List[str] = []

    drop_count = sum(1 for a in anomaly.anomalies if a.detector_name == "power_irradiance_drop")
    periodic_count = sum(1 for a in anomaly.anomalies if a.detector_name == "periodic_pattern")

    if drop_count > 0:
        score += min(30.0, drop_count * 8.0)
        supporting.append(_fact(f"{drop_count} power-to-irradiance drop anomalies detected", drop_count))

    if periodic_count > 0:
        score += 20.0
        supporting.append(_fact("Repeated low-power daytime patterns detected — consistent with recurring shading", periodic_count))

    if "panel_id" not in df.columns and "string_id" not in df.columns:
        missing.append("String-level or panel-level power readings for localisation")

    if score < 10.0:
        return None

    missing.append("Site drone or camera inspection results")
    missing.append("Maintenance log entry (last cleaning date)")
    contradicting.append(_fact("Shading/soiling cannot be confirmed remotely from telemetry alone — physical inspection required."))

    return Hypothesis(
        hypothesis_id=_uid(),
        name="Possible Shading or Soiling",
        rank=0,
        score=round(score, 2),
        severity="maintenance",
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        required_assumptions=[
            "Irradiance sensor is unobstructed and reading correctly.",
            "Peer inverter comparison unavailable (no multi-inverter data supplied).",
        ],
        missing_measurements=missing,
        alternative_explanations=["Inverter underperformance", "Module degradation", "Sensor error"],
        recommended_verification="Inspect site-approved photographic evidence. Compare with peer inverter output if available.",
        ranking_explanation="Ranked by presence of power/irradiance drop anomalies and periodic patterns.",
        triggered_rule_ids=["RULE-004"],
        input_features_used=["power_kw", "irradiance_wm2"],
    )


def rule_module_performance(
    df: pd.DataFrame,
    quality: QualityReport,
    anomaly: AnomalySummary,
) -> Optional[Hypothesis]:
    """RULE-005: PV module or string performance issue."""
    score = 0.0
    supporting: List[EvidenceItem] = []
    contradicting: List[EvidenceItem] = []
    missing: List[str] = []

    drift_count = sum(1 for a in anomaly.anomalies if a.detector_name == "sensor_drift" and a.column == "power_kw")
    if drift_count > 0:
        score += 20.0
        supporting.append(_fact("Gradual power drift detected, possibly indicating module degradation", drift_count))

    if "voltage_v" in df.columns and "current_a" in df.columns:
        valid = df[["voltage_v", "current_a"]].dropna()
        if len(valid) > 20:
            v_cv = valid["voltage_v"].std() / (valid["voltage_v"].mean() + 1e-6)
            if v_cv > 0.3:
                score += 15.0
                supporting.append(_derived(f"Voltage variability (CV={v_cv:.2f}) may indicate string mismatch", round(v_cv, 3)))
    else:
        missing.append("voltage_v and current_a for IV-curve analysis")

    if "panel_id" not in df.columns:
        missing.append("Panel-level or string-level measurements for isolation")

    if score < 10.0:
        return None

    return Hypothesis(
        hypothesis_id=_uid(),
        name="PV Module or String Performance Issue",
        rank=0,
        score=round(score, 2),
        severity="maintenance",
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        required_assumptions=["Module rated capacity and age are unknown for this analysis."],
        missing_measurements=missing,
        alternative_explanations=["Shading", "Soiling", "Inverter clipping"],
        recommended_verification="Perform string-level IV-curve trace or thermal imaging inspection.",
        ranking_explanation="Ranked by power drift and voltage variability indicators.",
        triggered_rule_ids=["RULE-005"],
        input_features_used=["power_kw", "voltage_v", "current_a"],
    )


def rule_inverter_electrical(
    df: pd.DataFrame,
    quality: QualityReport,
    anomaly: AnomalySummary,
) -> Optional[Hypothesis]:
    """RULE-006: Inverter or electrical-path issue."""
    score = 0.0
    supporting: List[EvidenceItem] = []
    contradicting: List[EvidenceItem] = []
    missing: List[str] = []

    roc_count = sum(1 for a in anomaly.anomalies if a.detector_name == "rate_of_change" and a.column == "power_kw")
    flatline_p = sum(1 for a in anomaly.anomalies if a.detector_name == "flatline" and a.column == "power_kw")

    if roc_count > 2:
        score += min(25.0, roc_count * 5.0)
        supporting.append(_fact(f"{roc_count} sudden power step-changes detected (possible inverter trips)", roc_count))

    if flatline_p > 0:
        score += 20.0
        supporting.append(_fact(f"{flatline_p} flatline periods in power output", flatline_p))

    if "frequency_hz" in df.columns:
        freq_valid = df["frequency_hz"].dropna()
        if len(freq_valid) > 10:
            out_of_range = ((freq_valid < 49.5) | (freq_valid > 50.5)).sum()
            if out_of_range > 0:
                score += 15.0
                supporting.append(_fact(f"{out_of_range} frequency readings outside 49.5–50.5 Hz", out_of_range))
    else:
        missing.append("frequency_hz for grid anomaly detection")

    if "inverter_id" not in df.columns:
        missing.append("inverter_id for peer-inverter comparison")

    if score < 10.0:
        return None

    return Hypothesis(
        hypothesis_id=_uid(),
        name="Inverter or Electrical-Path Performance Issue",
        rank=0,
        score=round(score, 2),
        severity="operational",
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        required_assumptions=["AC-side measurements are from the inverter output, not a downstream meter."],
        missing_measurements=missing,
        alternative_explanations=["Grid curtailment", "Protection relay operation", "Maintenance"],
        recommended_verification="Check inverter event log and compare AC output with DC input (clipping analysis).",
        ranking_explanation="Ranked by rate-of-change spikes, flatline power events, and frequency anomalies.",
        triggered_rule_ids=["RULE-006"],
        input_features_used=["power_kw", "frequency_hz"],
    )


def rule_temperature_issue(
    df: pd.DataFrame,
    quality: QualityReport,
    anomaly: AnomalySummary,
) -> Optional[Hypothesis]:
    """RULE-007: Abnormal temperature affecting performance."""
    score = 0.0
    supporting: List[EvidenceItem] = []
    contradicting: List[EvidenceItem] = []
    missing: List[str] = []

    temp_anom_count = sum(1 for a in anomaly.anomalies if a.detector_name == "temperature_anomaly")
    if temp_anom_count > 0:
        score += 20.0
        supporting.append(_fact(f"{temp_anom_count} temperature readings outside physical limits", temp_anom_count))

    if "temperature_c" in df.columns and "power_kw" in df.columns:
        valid = df[["temperature_c", "power_kw"]].dropna()
        if len(valid) > 30:
            corr = valid["temperature_c"].corr(valid["power_kw"])
            if corr < -0.5:
                score += 15.0
                supporting.append(_derived(f"Negative correlation ({corr:.2f}) between temperature and power, consistent with thermal derating", round(corr, 2)))

    if score < 10.0:
        return None

    missing.append("Module datasheet temperature coefficient for quantitative derating estimate")

    return Hypothesis(
        hypothesis_id=_uid(),
        name="Abnormal Temperature Affecting Performance",
        rank=0,
        score=round(score, 2),
        severity="informational",
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        required_assumptions=["Temperature sensor reads ambient or module temperature (not specified in data)."],
        missing_measurements=missing,
        alternative_explanations=["Sensor misplacement", "Irradiance-driven temperature increase without performance impact"],
        recommended_verification="Verify temperature sensor placement and compare with local weather data.",
        ranking_explanation="Ranked by temperature anomaly count and temperature-power correlation.",
        triggered_rule_ids=["RULE-007"],
        input_features_used=["temperature_c", "power_kw"],
    )


def rule_unexpected_decline(
    df: pd.DataFrame,
    quality: QualityReport,
    anomaly: AnomalySummary,
) -> Optional[Hypothesis]:
    """RULE-008: Unexpected power decline without matching irradiance change."""
    score = 0.0
    supporting: List[EvidenceItem] = []
    contradicting: List[EvidenceItem] = []
    missing: List[str] = []

    drop_count = sum(1 for a in anomaly.anomalies if a.detector_name == "power_irradiance_drop")
    drift_count = sum(1 for a in anomaly.anomalies if a.detector_name == "sensor_drift")

    if drop_count > 0 and drift_count == 0:
        score += 25.0
        supporting.append(_fact(f"{drop_count} power-drop events without matching irradiance reduction", drop_count))

    if "irradiance_wm2" in df.columns and "power_kw" in df.columns:
        valid = df[["irradiance_wm2", "power_kw"]].dropna()
        if len(valid) > 30:
            median_irr = valid["irradiance_wm2"].median()
            daytime = valid[valid["irradiance_wm2"] > median_irr * 0.5]
            if len(daytime) > 10:
                power_trend = np.polyfit(range(len(daytime)), daytime["power_kw"].values, 1)[0]
                if power_trend < -0.05:
                    score += 20.0
                    supporting.append(_derived(f"Downward power trend (slope {power_trend:.4f}) detected during daylight periods", round(power_trend, 4)))

    if score < 10.0:
        return None

    missing.append("Historical baseline dataset for trend comparison")
    missing.append("Maintenance records (module cleaning, inverter resets)")

    return Hypothesis(
        hypothesis_id=_uid(),
        name="Unexpected Power Decline",
        rank=0,
        score=round(score, 2),
        severity="operational",
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        required_assumptions=["Irradiance sensor is functioning correctly."],
        missing_measurements=missing,
        alternative_explanations=["Seasonal irradiance variation", "Progressive shading", "Inverter derating"],
        recommended_verification="Compare current period with same period in prior year if historical data is available.",
        ranking_explanation="Ranked by power-to-irradiance drop events and daytime power trend.",
        triggered_rule_ids=["RULE-008"],
        input_features_used=["power_kw", "irradiance_wm2"],
    )


def rule_insufficient_evidence(
    df: pd.DataFrame,
    quality: QualityReport,
    anomaly: AnomalySummary,
    other_hypotheses: List[Hypothesis],
) -> Hypothesis:
    """RULE-009: Insufficient evidence for diagnosis — always present as fallback."""
    reasons: List[EvidenceItem] = []
    if quality.total_rows < 10:
        reasons.append(_fact("Dataset is very small — fewer than 10 rows."))
    if quality.quality_score < 40.0:
        reasons.append(_derived(f"Data quality score ({quality.quality_score}) is low — analysis reliability limited."))
    if "irradiance_wm2" not in df.columns:
        reasons.append(_fact("Irradiance data absent — cannot assess solar resource."))
    if "power_kw" not in df.columns:
        reasons.append(_fact("Power data absent — cannot assess generation."))
    if len(other_hypotheses) == 0:
        reasons.append(_fact("No other hypotheses generated — insufficient signal in the data."))

    return Hypothesis(
        hypothesis_id=_uid(),
        name="Insufficient Evidence / Unknown Cause",
        rank=999,
        score=0.0,
        severity="informational",
        supporting_evidence=reasons or [_fact("All other hypotheses have been considered.")],
        contradicting_evidence=[],
        required_assumptions=[],
        missing_measurements=["More data points", "Additional sensor channels", "Equipment status logs"],
        alternative_explanations=["Any of the above hypotheses may apply with more data."],
        recommended_verification="Collect at least 7 days of clean data with all required channels before drawing conclusions.",
        ranking_explanation="Default fallback: ranked last when no other hypothesis has sufficient evidence.",
        triggered_rule_ids=["RULE-009"],
        input_features_used=[],
    )


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def generate_recommendations(hypotheses: List[Hypothesis]) -> List[Recommendation]:
    recs: List[Recommendation] = []
    hyp_names = [h.name for h in hypotheses if h.rank < 900]

    if any("Telemetry" in n or "Communication" in n for n in hyp_names):
        recs.append(Recommendation(
            recommendation_id=_uid(),
            test_name="Check Logger Connectivity and Timestamps",
            reason="Data gaps and invalid timestamps suggest a communication or logger fault.",
            hypotheses_addressed=["Telemetry / Communication Failure"],
            evidence_required=["Logger connection log", "SCADA/monitoring event log"],
            expected_observation="Identify outage window, connection errors, or clock drift in logger.",
            how_result_changes_diagnosis="If a communication fault is confirmed, telemetry gaps explain the anomalies. If connectivity is healthy, look for sensor or inverter faults.",
            priority="high",
            estimated_effort="15–30 minutes for experienced O&M technician",
            safety_note=None,
        ))

    if any("Irradiance Sensor" in n for n in hyp_names):
        recs.append(Recommendation(
            recommendation_id=_uid(),
            test_name="Compare with Calibrated Irradiance Reference Sensor",
            reason="Possible irradiance sensor drift or failure detected.",
            hypotheses_addressed=["Irradiance Sensor Drift or Failure", "Reduced Solar Resource / Cloud Passage"],
            evidence_required=["Co-located calibrated reference pyranometer", "NWP model irradiance estimate"],
            expected_observation="Agreement or significant deviation between site sensor and reference.",
            how_result_changes_diagnosis="Deviation >10% indicates sensor fault. Agreement suggests genuine resource reduction.",
            priority="high",
            estimated_effort="Varies — reference data may be available remotely; physical inspection may need a site visit",
            safety_note=None,
        ))

    if any("Shading" in n or "Soiling" in n for n in hyp_names):
        recs.append(Recommendation(
            recommendation_id=_uid(),
            test_name="Inspect Site for Shading or Soiling Evidence",
            reason="Power drops relative to irradiance are consistent with partial shading or module soiling.",
            hypotheses_addressed=["Possible Shading or Soiling"],
            evidence_required=["Approved site photographic evidence", "Maintenance log"],
            expected_observation="Visible soiling layer, shadow from nearby obstruction, or bird droppings.",
            how_result_changes_diagnosis="Confirmed soiling supports cleaning intervention. Confirmed shading may require design review.",
            priority="medium",
            estimated_effort="1–4 hours for site inspection",
            safety_note="Follow applicable safety procedures for working at heights on module surfaces.",
        ))

    if any("Inverter" in n for n in hyp_names):
        recs.append(Recommendation(
            recommendation_id=_uid(),
            test_name="Compare AC Output with DC Input (Inverter Efficiency Check)",
            reason="Sudden power changes may indicate inverter trips or AC-path issues.",
            hypotheses_addressed=["Inverter or Electrical-Path Performance Issue"],
            evidence_required=["DC input measurements (voltage, current)", "AC output measurements"],
            expected_observation="Large efficiency drop or mismatch between DC input and AC output.",
            how_result_changes_diagnosis="DC-AC mismatch supports inverter fault. Consistent ratio rules out inverter.",
            priority="high",
            estimated_effort="Retrievable from inverter monitoring system — may be immediate",
            safety_note="Do not access live electrical panels without appropriate qualification and lockout/tagout procedures.",
        ))

    if any("Module" in n or "String" in n for n in hyp_names):
        recs.append(Recommendation(
            recommendation_id=_uid(),
            test_name="Perform String-Level IV-Curve Trace",
            reason="Possible module or string performance degradation detected.",
            hypotheses_addressed=["PV Module or String Performance Issue"],
            evidence_required=["String-level IV-curve measurement equipment"],
            expected_observation="Fill-factor reduction, Voc or Isc anomalies indicating cell or module damage.",
            how_result_changes_diagnosis="IV-curve deviation confirms module/string issue. Normal curve rules it out.",
            priority="medium",
            estimated_effort="Half-day site visit with IV-curve tracer equipment",
            safety_note="Only qualified personnel should perform electrical measurements on live strings.",
        ))

    if len(recs) == 0:
        recs.append(Recommendation(
            recommendation_id=_uid(),
            test_name="Collect Additional Telemetry",
            reason="Insufficient evidence to distinguish between competing hypotheses.",
            hypotheses_addressed=["Insufficient Evidence / Unknown Cause"],
            evidence_required=["At least 7 days of complete data across all channels"],
            expected_observation="Patterns that distinguish a specific fault type or confirm healthy operation.",
            how_result_changes_diagnosis="More data will allow the engine to distinguish faults from resource variation.",
            priority="low",
            estimated_effort="7+ days of normal monitoring",
            safety_note=None,
        ))

    return recs


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_diagnosis(
    df: pd.DataFrame,
    quality: QualityReport,
    anomaly: AnomalySummary,
    active_rules: Optional[List[str]] = None,
) -> tuple[DiagnosisReport, List[Recommendation]]:
    """Run all active diagnostic rules and return ranked hypotheses + recommendations."""
    enabled = set(active_rules or [
        "telemetry_failure", "sensor_drift", "reduced_resource",
        "shading_soiling", "module_performance", "inverter_electrical",
        "temperature_issue", "unexpected_decline",
    ])

    candidates: List[Hypothesis] = []

    rule_map = {
        "telemetry_failure": rule_telemetry_failure,
        "sensor_drift": rule_sensor_drift,
        "reduced_resource": rule_reduced_resource,
        "shading_soiling": rule_shading_soiling,
        "module_performance": rule_module_performance,
        "inverter_electrical": rule_inverter_electrical,
        "temperature_issue": rule_temperature_issue,
        "unexpected_decline": rule_unexpected_decline,
    }

    for name, fn in rule_map.items():
        if name not in enabled:
            continue
        try:
            h = fn(df, quality, anomaly)
            if h is not None:
                candidates.append(h)
        except Exception as exc:
            pass  # Rules must never crash the pipeline

    # Sort and assign ranks
    candidates.sort(key=lambda h: h.score, reverse=True)
    for rank, h in enumerate(candidates):
        h.rank = rank + 1

    # Always add insufficient_evidence as final fallback
    fallback = rule_insufficient_evidence(df, quality, anomaly, candidates)
    fallback.rank = len(candidates) + 1

    all_hypotheses = candidates + [fallback]
    insufficient = len(candidates) == 0 or all(h.score < 5.0 for h in candidates)

    evidence_summary = {
        "anomaly_count": anomaly.total_anomalies,
        "quality_score": quality.quality_score,
        "total_rows": quality.total_rows,
        "has_irradiance": "irradiance_wm2" in df.columns,
        "has_power": "power_kw" in df.columns,
        "has_temperature": "temperature_c" in df.columns,
        "has_voltage": "voltage_v" in df.columns,
        "has_current": "current_a" in df.columns,
    }

    report = DiagnosisReport(
        hypotheses=all_hypotheses,
        uncertainty_note=(
            "Hypothesis scores are heuristic values derived from rule-based pattern matching. "
            "They are NOT probabilities. Competing explanations may apply simultaneously. "
            "Always verify diagnoses with physical inspection and equipment logs before acting."
        ),
        competing_causes_note=(
            "Multiple hypotheses may be active concurrently. The ranked list shows relative evidence strength, "
            "not mutual exclusivity."
        ),
        insufficient_evidence=insufficient,
        evidence_summary=evidence_summary,
    )

    recommendations = generate_recommendations(candidates)
    return report, recommendations
