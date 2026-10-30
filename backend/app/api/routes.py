"""FastAPI router — all ECO-SHIELD API endpoints."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse

from app.analysis.scenarios import (
    SCENARIO_META,
    get_scenario_detail,
    get_scenario_summary,
    list_scenarios,
)
from app.schemas.models import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisSummary,
    AppSettings,
    CompareResponse,
    DataSource,
    DatasetValidationResponse,
    ErrorResponse,
    HealthResponse,
    ScenarioDetail,
    ScenarioSummary,
)
from app.services.analysis_service import (
    export_analysis_csv,
    get_analysis_result,
    list_analysis_summaries,
    persist_dataset,
    persist_scenario_dataset,
    run_analysis,
    validate_dataset,
)
from app.services.settings_service import load_settings, save_settings
from app.storage.database import get_conn, get_analysis

router = APIRouter()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Health check endpoint."""
    db_status = "ok"
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1").fetchone()
    except Exception:
        db_status = "error"

    return HealthResponse(
        status="ok",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        database=db_status,
    )


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

@router.get("/scenarios", response_model=List[ScenarioSummary], tags=["Scenarios"])
async def get_scenarios():
    """List all available synthetic scenario definitions."""
    return list_scenarios()


@router.get("/scenarios/{scenario_id}", response_model=ScenarioDetail, tags=["Scenarios"])
async def get_scenario(scenario_id: str):
    """Get detailed metadata for a specific scenario."""
    if scenario_id not in SCENARIO_META:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
    return get_scenario_detail(scenario_id)


# ---------------------------------------------------------------------------
# Dataset validation
# ---------------------------------------------------------------------------

@router.post("/datasets/validate", response_model=DatasetValidationResponse, tags=["Datasets"])
async def validate_csv(file: UploadFile = File(...)):
    """Validate an uploaded CSV file without persisting it."""
    settings = load_settings()
    if file.filename is None or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum is {settings.max_upload_size_mb} MB.",
        )
    try:
        return validate_dataset(content, file.filename or "upload.csv", settings)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=AnalysisResult, tags=["Analysis"])
async def analyze(request: AnalysisRequest):
    """Run analysis pipeline on a previously validated dataset."""
    settings = load_settings()
    try:
        return run_analysis(request.dataset_id, settings, request.config_overrides)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Analysis pipeline encountered an error.")


@router.post("/analyze-csv", response_model=AnalysisResult, tags=["Analysis"])
async def analyze_csv(file: UploadFile = File(...)):
    """Upload a CSV and immediately run the full analysis pipeline."""
    settings = load_settings()
    if file.filename is None or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Max: {settings.max_upload_size_mb} MB.")

    try:
        dataset_id, _ = persist_dataset(content, file.filename or "upload.csv", DataSource.UPLOAD, settings)
        return run_analysis(dataset_id, settings)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Analysis failed. Check file format and required columns.")


@router.post("/analyze-scenario/{scenario_id}", response_model=AnalysisResult, tags=["Analysis"])
async def analyze_scenario(scenario_id: str):
    """Generate a scenario dataset and run the full analysis pipeline."""
    if scenario_id not in SCENARIO_META:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
    settings = load_settings()
    try:
        dataset_id, _ = persist_scenario_dataset(scenario_id, settings)
        return run_analysis(dataset_id, settings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scenario analysis failed: {e}")


# ---------------------------------------------------------------------------
# Analysis history
# ---------------------------------------------------------------------------

@router.get("/analyses", response_model=List[AnalysisSummary], tags=["Analysis History"])
async def list_analyses_endpoint(
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List analysis summaries with optional filtering."""
    return list_analysis_summaries(source=source, limit=limit, offset=offset)


# NOTE: /analyses/compare MUST be declared before /analyses/{analysis_id} so that
# FastAPI does not match the literal string "compare" as a path parameter.
@router.get("/analyses/compare", response_model=CompareResponse, tags=["Analysis History"])
async def compare_analyses(
    first_id: str = Query(...),
    second_id: str = Query(...),
):
    """Compare two analysis results."""
    a = get_analysis_result(first_id)
    b = get_analysis_result(second_id)
    if a is None:
        raise HTTPException(status_code=404, detail=f"Analysis '{first_id}' not found.")
    if b is None:
        raise HTTPException(status_code=404, detail=f"Analysis '{second_id}' not found.")

    def _summary(r: AnalysisResult) -> AnalysisSummary:
        hyps = r.diagnosis.hypotheses if hasattr(r.diagnosis, "hypotheses") else (r.diagnosis.get("hypotheses", []) if isinstance(r.diagnosis, dict) else [])
        top = None
        if hyps:
            ranked = [h for h in hyps if (h.rank if hasattr(h, "rank") else h.get("rank", 999)) < 900]
            if ranked:
                best = min(ranked, key=lambda h: h.rank if hasattr(h, "rank") else h.get("rank", 999))
                top = best.name if hasattr(best, "name") else best.get("name")
        qr = r.quality_report if not isinstance(r.quality_report, dict) else type("Q", (), r.quality_report)()
        an = r.anomaly_summary if not isinstance(r.anomaly_summary, dict) else type("A", (), r.anomaly_summary)()
        qs = r.quality_report.quality_score if hasattr(r.quality_report, "quality_score") else r.quality_report.get("quality_score", 0)
        ac = r.anomaly_summary.total_anomalies if hasattr(r.anomaly_summary, "total_anomalies") else r.anomaly_summary.get("total_anomalies", 0)
        tr = r.quality_report.total_rows if hasattr(r.quality_report, "total_rows") else r.quality_report.get("total_rows", 0)
        return AnalysisSummary(
            analysis_id=r.analysis_id,
            status=r.status,
            created_at=r.created_at,
            dataset_id=r.dataset_id,
            source=r.source,
            quality_score=qs,
            anomaly_count=ac,
            top_hypothesis=top,
            row_count=tr,
        )

    qs_a = a.quality_report.quality_score if hasattr(a.quality_report, "quality_score") else a.quality_report.get("quality_score", 0)
    qs_b = b.quality_report.quality_score if hasattr(b.quality_report, "quality_score") else b.quality_report.get("quality_score", 0)
    an_a = a.anomaly_summary.total_anomalies if hasattr(a.anomaly_summary, "total_anomalies") else a.anomaly_summary.get("total_anomalies", 0)
    an_b = b.anomaly_summary.total_anomalies if hasattr(b.anomaly_summary, "total_anomalies") else b.anomaly_summary.get("total_anomalies", 0)

    return CompareResponse(
        first_id=first_id,
        second_id=second_id,
        first_summary=_summary(a),
        second_summary=_summary(b),
        differences={
            "quality_score_delta": round(qs_b - qs_a, 2),
            "anomaly_count_delta": an_b - an_a,
            "first_created": str(a.created_at),
            "second_created": str(b.created_at),
        },
    )


@router.get("/analyses/{analysis_id}", response_model=AnalysisResult, tags=["Analysis History"])
async def get_analysis_endpoint(analysis_id: str):
    """Retrieve a full analysis result by ID."""
    result = get_analysis_result(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found.")
    return result


@router.get("/analyses/{analysis_id}/report", tags=["Analysis History"])
async def download_report(analysis_id: str):
    """Download a full analysis result as a JSON report."""
    result = get_analysis_result(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found.")
    return JSONResponse(
        content=result.model_dump(mode="json"),
        headers={"Content-Disposition": f'attachment; filename="ecoshield_report_{analysis_id[:8]}.json"'},
    )


@router.get("/analyses/{analysis_id}/csv", tags=["Analysis History"])
async def download_anomaly_csv(analysis_id: str):
    """Download anomaly records for an analysis as CSV."""
    csv_data = export_analysis_csv(analysis_id)
    if csv_data is None:
        raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found.")
    return PlainTextResponse(
        content=csv_data,
        headers={
            "Content-Disposition": f'attachment; filename="anomalies_{analysis_id[:8]}.csv"',
            "Content-Type": "text/csv",
        },
    )


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@router.get("/settings", response_model=AppSettings, tags=["Settings"])
async def get_settings_endpoint():
    """Retrieve current application settings."""
    return load_settings()


@router.put("/settings", response_model=AppSettings, tags=["Settings"])
async def update_settings(settings: AppSettings):
    """Update and persist application settings."""
    return save_settings(settings)
