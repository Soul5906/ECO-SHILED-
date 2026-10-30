"""Scenario simulator — generates deterministic synthetic datasets for testing."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from app.schemas.models import ScenarioDetail, ScenarioSummary


# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------

SCENARIO_META: Dict[str, Dict[str, Any]] = {
    "normal_operation": {
        "name": "Normal Operation",
        "description": "Healthy solar array over 3 days with expected diurnal patterns. No injected faults.",
        "tags": ["baseline", "healthy", "reference"],
        "purpose": "Provides a clean baseline for comparison and verifying that no false positives are generated under normal conditions.",
        "injected_conditions": [],
        "expected_anomaly_types": [],
        "seed": 42,
        "duration_hours": 72,
        "interval_minutes": 15,
    },
    "power_decline": {
        "name": "Gradual Power Decline",
        "description": "Power output gradually decreases over 5 days while irradiance remains consistent.",
        "tags": ["fault", "degradation", "inverter"],
        "purpose": "Tests detection of slow degradation trends, distinct from resource variation.",
        "injected_conditions": ["power_decline_trend"],
        "expected_anomaly_types": ["sensor_drift", "power_irradiance_drop"],
        "seed": 100,
        "duration_hours": 120,
        "interval_minutes": 15,
    },
    "irradiance_sensor_shift": {
        "name": "Irradiance Sensor Offset",
        "description": "Irradiance sensor develops a step offset mid-dataset simulating calibration drift.",
        "tags": ["fault", "sensor", "irradiance"],
        "purpose": "Tests ability to detect sensor drift separate from real resource changes.",
        "injected_conditions": ["irradiance_step_offset"],
        "expected_anomaly_types": ["sensor_drift", "mad_outlier"],
        "seed": 200,
        "duration_hours": 72,
        "interval_minutes": 15,
    },
    "missing_telemetry": {
        "name": "Missing Telemetry Gaps",
        "description": "Dataset with multiple large gaps simulating logger outages.",
        "tags": ["fault", "communication", "gaps"],
        "purpose": "Tests gap detection and telemetry failure diagnosis.",
        "injected_conditions": ["multiple_data_gaps"],
        "expected_anomaly_types": ["missing_gaps"],
        "seed": 300,
        "duration_hours": 72,
        "interval_minutes": 15,
    },
    "duplicate_timestamps": {
        "name": "Duplicate Timestamps",
        "description": "Dataset with intentionally duplicated rows and timestamps.",
        "tags": ["data_quality", "duplicates"],
        "purpose": "Tests duplicate detection and data-quality reporting.",
        "injected_conditions": ["duplicate_rows"],
        "expected_anomaly_types": ["duplicate_timestamps"],
        "seed": 400,
        "duration_hours": 48,
        "interval_minutes": 15,
    },
    "cloud_passage": {
        "name": "Cloud Passage Event",
        "description": "Rapid irradiance and power fluctuations simulating cloud transit.",
        "tags": ["weather", "variability", "irradiance"],
        "purpose": "Tests rate-of-change and resource-reduction detection against weather-driven events.",
        "injected_conditions": ["cloud_ramps"],
        "expected_anomaly_types": ["rate_of_change", "mad_outlier"],
        "seed": 500,
        "duration_hours": 24,
        "interval_minutes": 5,
    },
    "power_spikes": {
        "name": "Sudden Power Spikes",
        "description": "Short-duration power spikes that exceed rated capacity.",
        "tags": ["fault", "spike", "inverter"],
        "purpose": "Tests spike detection and physical-limit validation.",
        "injected_conditions": ["power_spikes"],
        "expected_anomaly_types": ["mad_outlier", "rate_of_change"],
        "seed": 600,
        "duration_hours": 48,
        "interval_minutes": 15,
    },
    "flatline_sensor": {
        "name": "Flatlined Sensor",
        "description": "Power or irradiance sensor gets stuck at a constant value mid-dataset.",
        "tags": ["fault", "sensor", "flatline"],
        "purpose": "Tests flatline and constant-sensor detection.",
        "injected_conditions": ["flatline_irradiance"],
        "expected_anomaly_types": ["flatline", "constant_sensor"],
        "seed": 700,
        "duration_hours": 48,
        "interval_minutes": 15,
    },
    "irregular_sampling": {
        "name": "Irregular Sampling Interval",
        "description": "Dataset with inconsistent time intervals between readings.",
        "tags": ["data_quality", "sampling"],
        "purpose": "Tests irregular-interval detection in the quality engine.",
        "injected_conditions": ["irregular_timestamps"],
        "expected_anomaly_types": ["missing_gaps"],
        "seed": 800,
        "duration_hours": 48,
        "interval_minutes": 15,
    },
    "conflicting_sensors": {
        "name": "Conflicting Sensor Measurements",
        "description": "Power and irradiance give contradictory signals simultaneously.",
        "tags": ["ambiguous", "sensors", "conflict"],
        "purpose": "Tests engine behaviour under conflicting evidence and multiple competing hypotheses.",
        "injected_conditions": ["contradictory_power_irradiance"],
        "expected_anomaly_types": ["power_irradiance_drop", "sensor_drift"],
        "seed": 900,
        "duration_hours": 48,
        "interval_minutes": 15,
    },
    "high_temperature": {
        "name": "High Temperature Event",
        "description": "Extended high-temperature period simulating thermal derating.",
        "tags": ["weather", "temperature", "derating"],
        "purpose": "Tests temperature-anomaly detection and temperature-power correlation analysis.",
        "injected_conditions": ["high_temperature_sustained"],
        "expected_anomaly_types": ["temperature_anomaly"],
        "seed": 1000,
        "duration_hours": 72,
        "interval_minutes": 15,
    },
    "ambiguous_evidence": {
        "name": "Ambiguous / Insufficient Evidence",
        "description": "Very short dataset with minimal signal — engine should report insufficient evidence.",
        "tags": ["edge_case", "insufficient_data"],
        "purpose": "Verifies that the engine does not force a diagnosis when evidence is inadequate.",
        "injected_conditions": ["minimal_rows"],
        "expected_anomaly_types": [],
        "seed": 1100,
        "duration_hours": 2,
        "interval_minutes": 60,
    },
}


# ---------------------------------------------------------------------------
# Solar model helper
# ---------------------------------------------------------------------------

def _solar_irradiance(hour: float, day: int = 0) -> float:
    """Simple bell-curve irradiance model (peak at solar noon)."""
    rng = np.random.default_rng(seed=42 + day)
    cloud_factor = 1.0 + rng.normal(0, 0.05)
    cloud_factor = max(0.1, min(1.2, cloud_factor))
    h = hour % 24
    if h < 6 or h > 20:
        return 0.0
    peak = 900 * cloud_factor * np.sin(np.pi * (h - 6) / 14)
    return max(0.0, peak)


def _generate_base_df(
    seed: int,
    duration_hours: float,
    interval_minutes: int,
) -> pd.DataFrame:
    """Generate a clean base dataset."""
    rng = np.random.default_rng(seed=seed)
    start = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    n = int(duration_hours * 60 / interval_minutes)
    timestamps = [start + timedelta(minutes=i * interval_minutes) for i in range(n)]

    irradiance = []
    power = []
    temperature = []

    for i, ts in enumerate(timestamps):
        hour = ts.hour + ts.minute / 60.0
        day = i // (96 if interval_minutes == 15 else 288)
        irr = _solar_irradiance(hour, day)
        irr = max(0.0, irr + rng.normal(0, 15))
        pwr = max(0.0, irr * 0.18 * (1 + rng.normal(0, 0.03)))  # ~18% efficiency
        temp = 25.0 + (irr / 900.0) * 20.0 + rng.normal(0, 1.5)
        irradiance.append(round(irr, 2))
        power.append(round(pwr, 3))
        temperature.append(round(temp, 2))

    df = pd.DataFrame({
        "timestamp": timestamps,
        "power_kw": power,
        "irradiance_wm2": irradiance,
        "temperature_c": temperature,
        "inverter_id": "INV-01",
        "site_id": "SITE-001",
    })
    return df


# ---------------------------------------------------------------------------
# Injected fault functions
# ---------------------------------------------------------------------------

def _inject_power_decline(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    n = len(df)
    decline = np.linspace(1.0, 0.5, n)
    df["power_kw"] = (df["power_kw"] * decline).round(3)
    return df


def _inject_irradiance_offset(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    midpoint = len(df) // 2
    df.loc[df.index[midpoint:], "irradiance_wm2"] = (
        df.loc[df.index[midpoint:], "irradiance_wm2"] * 0.65
    ).round(2)
    return df


def _inject_gaps(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    n = len(df)
    gap_starts = sorted(rng.choice(n // 2, size=3, replace=False))
    for gs in gap_starts:
        gap_len = rng.integers(20, 50)
        drop_indices = df.index[int(gs): int(gs) + int(gap_len)]
        df = df.drop(drop_indices)
    return df.reset_index(drop=True)


def _inject_duplicates(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    dup_rows = df.sample(n=min(20, len(df) // 10), random_state=int(rng.integers(0, 9999)))
    df = pd.concat([df, dup_rows]).sort_values("timestamp").reset_index(drop=True)
    return df


def _inject_cloud_ramps(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    n = len(df)
    for _ in range(10):
        start = int(rng.integers(0, n - 20))
        duration = int(rng.integers(6, 24))
        scale = rng.uniform(0.1, 0.4)
        for j in range(duration):
            idx = start + j
            if idx < n:
                df.loc[df.index[idx], "irradiance_wm2"] = max(0.0, df.iloc[idx]["irradiance_wm2"] * scale)
                df.loc[df.index[idx], "power_kw"] = max(0.0, df.iloc[idx]["power_kw"] * scale)
    return df


def _inject_spikes(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    spike_indices = rng.choice(len(df), size=8, replace=False)
    for i in spike_indices:
        df.loc[df.index[i], "power_kw"] = round(float(df.iloc[i]["power_kw"]) * rng.uniform(3, 6), 3)
    return df


def _inject_flatline(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    midpoint = len(df) // 3
    end = midpoint + min(60, len(df) // 3)
    fixed_val = float(df.iloc[midpoint]["irradiance_wm2"])
    df.loc[df.index[midpoint:end], "irradiance_wm2"] = fixed_val
    return df


def _inject_irregular_timestamps(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    offsets = rng.integers(-20, 20, size=len(df))
    df["timestamp"] = df["timestamp"] + pd.to_timedelta(offsets, unit="min")
    return df.sort_values("timestamp").reset_index(drop=True)


def _inject_contradictory(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    # Power drops while irradiance stays high
    start = len(df) // 3
    end = 2 * len(df) // 3
    df.loc[df.index[start:end], "power_kw"] = 0.0
    return df


def _inject_high_temperature(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    start = len(df) // 4
    end = 3 * len(df) // 4
    df.loc[df.index[start:end], "temperature_c"] = df.loc[df.index[start:end], "temperature_c"] + 40.0
    df["power_kw"] = (df["power_kw"] * (1 - 0.004 * (df["temperature_c"] - 25).clip(lower=0))).clip(lower=0)
    return df


INJECTORS = {
    "power_decline_trend": _inject_power_decline,
    "irradiance_step_offset": _inject_irradiance_offset,
    "multiple_data_gaps": _inject_gaps,
    "duplicate_rows": _inject_duplicates,
    "cloud_ramps": _inject_cloud_ramps,
    "power_spikes": _inject_spikes,
    "flatline_irradiance": _inject_flatline,
    "irregular_timestamps": _inject_irregular_timestamps,
    "contradictory_power_irradiance": _inject_contradictory,
    "high_temperature_sustained": _inject_high_temperature,
    "minimal_rows": None,
}


def generate_scenario(scenario_id: str) -> pd.DataFrame:
    """Generate a labelled synthetic DataFrame for the given scenario."""
    meta = SCENARIO_META.get(scenario_id)
    if meta is None:
        raise ValueError(f"Unknown scenario: '{scenario_id}'")

    seed = meta["seed"]
    rng = np.random.default_rng(seed=seed)

    if scenario_id == "ambiguous_evidence":
        # Tiny dataset
        start = datetime(2024, 6, 1, 10, 0, tzinfo=timezone.utc)
        timestamps = [start + timedelta(hours=i) for i in range(3)]
        return pd.DataFrame({
            "timestamp": timestamps,
            "power_kw": [1.2, 1.1, 1.0],
            "irradiance_wm2": [500.0, 490.0, 480.0],
            "temperature_c": [28.0, 28.5, 29.0],
            "inverter_id": "INV-01",
            "site_id": "SITE-001",
        })

    df = _generate_base_df(seed, meta["duration_hours"], meta["interval_minutes"])

    for condition in meta.get("injected_conditions", []):
        injector = INJECTORS.get(condition)
        if injector is not None:
            df = injector(df, rng)

    df["_synthetic"] = True
    df["_scenario_id"] = scenario_id
    return df


def get_scenario_summary(scenario_id: str) -> ScenarioSummary:
    meta = SCENARIO_META[scenario_id]
    df = generate_scenario(scenario_id)
    duration = meta["duration_hours"]
    return ScenarioSummary(
        id=scenario_id,
        name=meta["name"],
        description=meta["description"],
        tags=meta["tags"],
        row_count=len(df),
        duration_hours=duration,
        injected_conditions=meta["injected_conditions"],
    )


def get_scenario_detail(scenario_id: str) -> ScenarioDetail:
    meta = SCENARIO_META[scenario_id]
    df = generate_scenario(scenario_id)
    return ScenarioDetail(
        id=scenario_id,
        name=meta["name"],
        description=meta["description"],
        tags=meta["tags"],
        row_count=len(df),
        duration_hours=meta["duration_hours"],
        injected_conditions=meta["injected_conditions"],
        purpose=meta["purpose"],
        seed=meta["seed"],
        expected_anomaly_types=meta["expected_anomaly_types"],
        columns=[c for c in df.columns if not c.startswith("_")],
    )


def list_scenarios() -> List[ScenarioSummary]:
    return [get_scenario_summary(sid) for sid in SCENARIO_META]
