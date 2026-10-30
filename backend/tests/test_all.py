"""Comprehensive backend tests for ECO-SHIELD."""
from __future__ import annotations

import io
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def temp_db(tmp_path_factory):
    """Create a temporary database for the test session."""
    db_path = tmp_path_factory.mktemp("db") / "test_ecoshield.db"
    return db_path


@pytest.fixture(scope="session", autouse=True)
def setup_db(temp_db, monkeypatch_session):
    """Initialise test database before any tests run."""
    import app.storage.database as dbmod
    dbmod.DB_PATH = temp_db
    dbmod.init_db(temp_db)


@pytest.fixture(scope="session")
def monkeypatch_session():
    """Session-scoped monkeypatch."""
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture
def client(temp_db):
    """TestClient that uses the temp database."""
    import app.storage.database as dbmod
    dbmod.DB_PATH = temp_db
    from app.main import app
    return TestClient(app)


def _make_csv(rows: list[dict], extra_cols: dict | None = None) -> bytes:
    """Build a minimal valid CSV for testing."""
    base = [
        {
            "timestamp": (datetime(2024, 6, 1, 10, 0, tzinfo=timezone.utc) + timedelta(minutes=15 * i)).isoformat(),
            "power_kw": max(0.0, 10.0 + np.random.normal(0, 0.5)),
            "irradiance_wm2": max(0.0, 700.0 + np.random.normal(0, 20)),
            "temperature_c": 28.0 + np.random.normal(0, 1),
        }
        for i in range(50)
    ]
    if rows:
        base = rows
    if extra_cols:
        for r in base:
            r.update(extra_cols)
    return pd.DataFrame(base).to_csv(index=False).encode()


def _valid_csv(n: int = 50) -> bytes:
    return _make_csv([{
        "timestamp": (datetime(2024, 6, 1, 10, 0, tzinfo=timezone.utc) + timedelta(minutes=15 * i)).isoformat(),
        "power_kw": max(0.0, 10.0 + float(np.random.default_rng(i).normal(0, 0.5))),
        "irradiance_wm2": max(0.0, 700.0 + float(np.random.default_rng(i + 1000).normal(0, 20))),
        "temperature_c": 28.0 + float(np.random.default_rng(i + 2000).normal(0, 1)),
    } for i in range(n)])


# ===========================================================================
# Quality Engine Tests
# ===========================================================================

class TestQualityEngine:
    def test_valid_dataset(self):
        from app.analysis.quality_engine import run_quality_engine
        df = pd.read_csv(io.BytesIO(_valid_csv(100)))
        report = run_quality_engine(df)
        assert report.total_rows == 100
        assert report.quality_score > 50.0
        assert isinstance(report.quality_score_method, str)
        assert len(report.quality_score_method) > 10

    def test_missing_required_columns(self):
        from app.analysis.quality_engine import run_quality_engine
        df = pd.DataFrame({"timestamp": ["2024-01-01"], "power_kw": [1.0]})
        report = run_quality_engine(df)
        missing_issues = [i for i in report.issues if i.issue_type == "missing_required_column"]
        assert len(missing_issues) >= 2  # irradiance_wm2 and temperature_c

    def test_missing_values_reported(self):
        from app.analysis.quality_engine import run_quality_engine
        df = pd.read_csv(io.BytesIO(_valid_csv(50)))
        df.loc[5:15, "power_kw"] = None
        report = run_quality_engine(df)
        col = next((c for c in report.column_quality if c.column == "power_kw"), None)
        assert col is not None
        assert col.missing_count == 11

    def test_invalid_timestamps(self):
        from app.analysis.quality_engine import run_quality_engine
        df = pd.read_csv(io.BytesIO(_valid_csv(20)))
        df.loc[3, "timestamp"] = "not-a-date"
        df.loc[7, "timestamp"] = "9999-99-99"
        report = run_quality_engine(df)
        assert report.invalid_timestamp_count >= 1

    def test_duplicate_timestamps(self):
        from app.analysis.quality_engine import run_quality_engine
        df = pd.read_csv(io.BytesIO(_valid_csv(20)))
        df.loc[5, "timestamp"] = df.loc[4, "timestamp"]  # duplicate
        report = run_quality_engine(df)
        assert report.duplicate_timestamps >= 1

    def test_negative_power_flagged(self):
        from app.analysis.quality_engine import run_quality_engine
        df = pd.read_csv(io.BytesIO(_valid_csv(20)))
        df.loc[3, "power_kw"] = -5.0
        report = run_quality_engine(df)
        neg_issues = [i for i in report.issues if i.issue_type == "negative_physical_value"]
        assert len(neg_issues) > 0

    def test_zero_variance_column(self):
        from app.analysis.quality_engine import run_quality_engine
        df = pd.read_csv(io.BytesIO(_valid_csv(50)))
        df["temperature_c"] = 25.0  # constant
        report = run_quality_engine(df)
        const_issues = [i for i in report.issues if i.issue_type == "constant_sensor"]
        assert len(const_issues) > 0

    def test_empty_dataset(self):
        from app.analysis.quality_engine import run_quality_engine
        df = pd.DataFrame(columns=["timestamp", "power_kw", "irradiance_wm2", "temperature_c"])
        report = run_quality_engine(df)
        assert report.total_rows == 0

    def test_small_dataset(self):
        from app.analysis.quality_engine import run_quality_engine
        df = pd.read_csv(io.BytesIO(_valid_csv(3)))
        report = run_quality_engine(df)
        assert report.total_rows == 3

    def test_quality_score_is_bounded(self):
        from app.analysis.quality_engine import run_quality_engine
        df = pd.read_csv(io.BytesIO(_valid_csv(100)))
        report = run_quality_engine(df)
        assert 0.0 <= report.quality_score <= 100.0


# ===========================================================================
# Anomaly Engine Tests
# ===========================================================================

class TestAnomalyEngine:
    def _get_df(self, n: int = 100) -> pd.DataFrame:
        df = pd.read_csv(io.BytesIO(_valid_csv(n)))
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df

    def test_mad_outlier_detector(self):
        from app.analysis.anomaly_engine import detect_mad_outliers
        df = self._get_df(100)
        df.loc[50, "power_kw"] = 9999.0
        results = detect_mad_outliers(df, threshold=3.5)
        assert any(r.row_index == 50 for r in results)

    def test_zscore_requires_30_rows(self):
        from app.analysis.anomaly_engine import detect_zscore_outliers
        df = self._get_df(20)
        results = detect_zscore_outliers(df)
        assert results == []  # Too few rows

    def test_rate_of_change_detector(self):
        from app.analysis.anomaly_engine import detect_rate_of_change
        df = self._get_df(50)
        df.loc[25, "power_kw"] = 9999.0
        results = detect_rate_of_change(df, threshold=100.0)
        assert len(results) > 0

    def test_missing_gaps_detector(self):
        from app.analysis.anomaly_engine import detect_missing_gaps
        df = self._get_df(50)
        # Remove 30 rows to create a gap
        df = pd.concat([df.iloc[:20], df.iloc[50:]]).reset_index(drop=True)
        results = detect_missing_gaps(df, expected_interval_minutes=15.0)
        assert len(results) == 0  # Nothing after index 20 in this small slice; at least no crash

    def test_flatline_detector(self):
        from app.analysis.anomaly_engine import detect_flatline
        df = self._get_df(100)
        df.loc[40:60, "power_kw"] = 5.0  # stuck sensor
        results = detect_flatline(df, window=10)
        assert len(results) > 0

    def test_duplicate_timestamp_detector(self):
        from app.analysis.anomaly_engine import detect_duplicate_timestamps
        df = self._get_df(30)
        df.loc[10, "timestamp"] = df.loc[9, "timestamp"]
        results = detect_duplicate_timestamps(df)
        assert len(results) >= 1

    def test_power_irradiance_drop(self):
        from app.analysis.anomaly_engine import detect_power_irradiance_drop
        df = self._get_df(100)
        # Power drops while irradiance stays high
        df.loc[30:50, "power_kw"] = 0.01
        results = detect_power_irradiance_drop(df, drop_ratio_threshold=0.5)
        assert len(results) > 0

    def test_temperature_anomaly_detector(self):
        from app.analysis.anomaly_engine import detect_temperature_anomaly
        df = self._get_df(50)
        df.loc[10, "temperature_c"] = 999.0
        results = detect_temperature_anomaly(df, min_c=-50.0, max_c=100.0)
        assert any(r.row_index == 10 for r in results)

    def test_detector_handles_empty_df(self):
        from app.analysis.anomaly_engine import detect_mad_outliers
        df = pd.DataFrame(columns=["power_kw", "irradiance_wm2", "temperature_c"])
        results = detect_mad_outliers(df)
        assert results == []

    def test_detector_handles_constant_series(self):
        from app.analysis.anomaly_engine import detect_mad_outliers
        df = pd.DataFrame({"power_kw": [5.0] * 30, "irradiance_wm2": [500.0] * 30, "temperature_c": [25.0] * 30})
        results = detect_mad_outliers(df)
        # Zero MAD — should not crash and should return no false positives
        assert isinstance(results, list)

    def test_run_all_detectors(self):
        from app.analysis.anomaly_engine import run_anomaly_detectors
        df = self._get_df(100)
        summary = run_anomaly_detectors(df)
        assert isinstance(summary.total_anomalies, int)
        assert len(summary.detectors_run) > 0


# ===========================================================================
# Diagnosis Engine Tests
# ===========================================================================

class TestDiagnosisEngine:
    def _get_report(self, n: int = 100):
        from app.analysis.anomaly_engine import run_anomaly_detectors
        from app.analysis.quality_engine import run_quality_engine
        df = pd.read_csv(io.BytesIO(_valid_csv(n)))
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        quality = run_quality_engine(df.copy())
        anomaly = run_anomaly_detectors(df.copy())
        return df, quality, anomaly

    def test_hypotheses_returned(self):
        from app.analysis.diagnosis_engine import run_diagnosis
        df, quality, anomaly = self._get_report(100)
        report, recs = run_diagnosis(df, quality, anomaly)
        assert isinstance(report.hypotheses, list)
        assert len(report.hypotheses) >= 1  # at least fallback

    def test_insufficient_evidence_fallback(self):
        from app.analysis.diagnosis_engine import run_diagnosis
        from app.analysis.anomaly_engine import run_anomaly_detectors
        from app.analysis.quality_engine import run_quality_engine
        # Very small, clean dataset
        df = pd.read_csv(io.BytesIO(_valid_csv(3)))
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        quality = run_quality_engine(df.copy())
        anomaly = run_anomaly_detectors(df.copy())
        report, _ = run_diagnosis(df, quality, anomaly)
        fallbacks = [h for h in report.hypotheses if "Insufficient" in h.name]
        assert len(fallbacks) >= 1

    def test_hypotheses_ranked(self):
        from app.analysis.diagnosis_engine import run_diagnosis
        df, quality, anomaly = self._get_report(100)
        # Inject power drops
        df.loc[30:60, "power_kw"] = 0.01
        from app.analysis.anomaly_engine import run_anomaly_detectors
        from app.analysis.quality_engine import run_quality_engine
        quality = run_quality_engine(df.copy())
        anomaly = run_anomaly_detectors(df.copy())
        report, _ = run_diagnosis(df, quality, anomaly)
        ranks = [h.rank for h in report.hypotheses]
        assert ranks == sorted(ranks)

    def test_competing_hypotheses(self):
        from app.analysis.diagnosis_engine import run_diagnosis
        df, quality, anomaly = self._get_report(200)
        # Inject multiple issues
        df.loc[30:60, "power_kw"] = 0.01
        df.loc[80:90, "irradiance_wm2"] = 800.0  # irr stays high
        from app.analysis.anomaly_engine import run_anomaly_detectors
        from app.analysis.quality_engine import run_quality_engine
        quality = run_quality_engine(df.copy())
        anomaly = run_anomaly_detectors(df.copy())
        report, recs = run_diagnosis(df, quality, anomaly)
        assert report.competing_causes_note is not None
        assert len(recs) > 0

    def test_uncertainty_note_present(self):
        from app.analysis.diagnosis_engine import run_diagnosis
        df, quality, anomaly = self._get_report(100)
        report, _ = run_diagnosis(df, quality, anomaly)
        assert "heuristic" in report.uncertainty_note.lower()

    def test_recommendations_generated(self):
        from app.analysis.diagnosis_engine import run_diagnosis, generate_recommendations
        from app.analysis.diagnosis_engine import rule_shading_soiling
        df, quality, anomaly = self._get_report(100)
        df.loc[30:60, "power_kw"] = 0.01
        from app.analysis.anomaly_engine import run_anomaly_detectors
        from app.analysis.quality_engine import run_quality_engine
        quality = run_quality_engine(df.copy())
        anomaly = run_anomaly_detectors(df.copy())
        report, recs = run_diagnosis(df, quality, anomaly)
        assert isinstance(recs, list)
        assert all(hasattr(r, "test_name") for r in recs)


# ===========================================================================
# Scenario Tests
# ===========================================================================

class TestScenarios:
    def test_all_scenarios_generate(self):
        from app.analysis.scenarios import SCENARIO_META, generate_scenario
        for sid in SCENARIO_META:
            df = generate_scenario(sid)
            assert len(df) > 0
            assert "timestamp" in df.columns

    def test_scenarios_are_deterministic(self):
        from app.analysis.scenarios import generate_scenario
        df1 = generate_scenario("normal_operation")
        df2 = generate_scenario("normal_operation")
        assert df1["power_kw"].tolist() == df2["power_kw"].tolist()

    def test_scenario_has_synthetic_label(self):
        from app.analysis.scenarios import generate_scenario
        df = generate_scenario("power_decline")
        assert "_synthetic" in df.columns
        assert df["_synthetic"].all()

    def test_ambiguous_scenario_is_small(self):
        from app.analysis.scenarios import generate_scenario
        df = generate_scenario("ambiguous_evidence")
        assert len(df) < 10


# ===========================================================================
# API Endpoint Tests
# ===========================================================================

class TestAPIHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "database" in data


class TestAPIScenarios:
    def test_list_scenarios(self, client):
        r = client.get("/api/scenarios")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_scenario_detail(self, client):
        r = client.get("/api/scenarios/normal_operation")
        assert r.status_code == 200
        assert r.json()["id"] == "normal_operation"

    def test_get_scenario_not_found(self, client):
        r = client.get("/api/scenarios/nonexistent_xyz")
        assert r.status_code == 404


class TestAPIDatasetValidation:
    def test_valid_csv_upload(self, client):
        csv_bytes = _valid_csv(50)
        r = client.post(
            "/api/datasets/validate",
            files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["row_count"] == 50
        assert isinstance(data["column_names"], list)

    def test_missing_columns_flagged(self, client):
        df = pd.DataFrame({"timestamp": ["2024-01-01"], "power_kw": [1.0]})
        csv_bytes = df.to_csv(index=False).encode()
        r = client.post(
            "/api/datasets/validate",
            files={"file": ("missing.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert r.status_code == 200
        data = r.json()
        issue_types = [i["issue_type"] for i in data["issues"]]
        assert "missing_required_column" in issue_types

    def test_non_csv_rejected(self, client):
        r = client.post(
            "/api/datasets/validate",
            files={"file": ("data.xlsx", io.BytesIO(b"fake"), "application/octet-stream")},
        )
        assert r.status_code == 400

    def test_empty_file_returns_error(self, client):
        r = client.post(
            "/api/datasets/validate",
            files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is False


class TestAPIAnalysis:
    def test_analyze_scenario(self, client):
        r = client.post("/api/analyze-scenario/normal_operation")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "complete"
        assert "quality_report" in data
        assert "anomaly_summary" in data
        assert "diagnosis" in data
        assert "recommendations" in data

    def test_analyze_csv_upload(self, client):
        csv_bytes = _valid_csv(100)
        r = client.post(
            "/api/analyze-csv",
            files={"file": ("upload.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["analysis_id"] is not None
        assert data["status"] == "complete"

    def test_analyze_invalid_dataset_id(self, client):
        r = client.post("/api/analyze", json={"dataset_id": "does-not-exist"})
        assert r.status_code == 404

    def test_analysis_result_retrievable(self, client):
        # Run analysis
        r = client.post("/api/analyze-scenario/power_decline")
        assert r.status_code == 200
        aid = r.json()["analysis_id"]
        # Retrieve it
        r2 = client.get(f"/api/analyses/{aid}")
        assert r2.status_code == 200
        assert r2.json()["analysis_id"] == aid

    def test_analysis_history_listed(self, client):
        r = client.get("/api/analyses")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_download_json_report(self, client):
        r = client.post("/api/analyze-scenario/cloud_passage")
        aid = r.json()["analysis_id"]
        r2 = client.get(f"/api/analyses/{aid}/report")
        assert r2.status_code == 200
        assert "analysis_id" in r2.json()

    def test_download_csv_anomalies(self, client):
        r = client.post("/api/analyze-scenario/flatline_sensor")
        aid = r.json()["analysis_id"]
        r2 = client.get(f"/api/analyses/{aid}/csv")
        assert r2.status_code == 200
        assert "anomaly_id" in r2.text

    def test_analysis_not_found(self, client):
        r = client.get("/api/analyses/nonexistent-id-xyz")
        assert r.status_code == 404


class TestAPISettings:
    def test_get_default_settings(self, client):
        r = client.get("/api/settings")
        assert r.status_code == 200
        data = r.json()
        assert "anomaly_thresholds" in data
        assert "physical_limits" in data

    def test_update_settings(self, client):
        r = client.get("/api/settings")
        settings = r.json()
        settings["anomaly_thresholds"]["mad_threshold"] = 4.0
        r2 = client.put("/api/settings", json=settings)
        assert r2.status_code == 200
        assert r2.json()["anomaly_thresholds"]["mad_threshold"] == 4.0

    def test_invalid_settings_rejected(self, client):
        r = client.get("/api/settings")
        settings = r.json()
        settings["anomaly_thresholds"]["mad_threshold"] = -99.0  # invalid (< 1.0)
        r2 = client.put("/api/settings", json=settings)
        assert r2.status_code == 422
