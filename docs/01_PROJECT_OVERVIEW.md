# 1. Project Overview

## Purpose
ECO-SHIELD stands for **Evidence-Driven Clean Energy & Environmental Diagnostics**. It analyzes solar-energy telemetry to help users understand data-quality issues, unusual readings, possible fault causes, and useful next diagnostic tests.

## Problem addressed
Raw telemetry can contain missing values, duplicated timestamps, sensor drift, sudden power drops, or patterns that are difficult to interpret. ECO-SHIELD organizes those signals and explains why a possible cause was ranked.

## Processing flow
1. Select a synthetic scenario or upload a CSV.
2. Normalize and validate the dataset.
3. Calculate data-quality indicators.
4. Detect statistical anomalies.
5. Evaluate diagnostic rules.
6. Rank hypotheses and record evidence and caveats.
7. Recommend a next diagnostic check.
8. Save the analysis and export the report.

## Architecture
- **Frontend:** React + TypeScript + Vite.
- **Charts:** Recharts.
- **Backend:** Python + FastAPI.
- **Analysis:** Pandas + NumPy and transparent rules.
- **Persistence:** SQLite.
- **API docs:** FastAPI OpenAPI/Swagger.

## Intended users
- Students building a clean-energy hackathon prototype.
- Engineers exploring telemetry and data quality.
- Developers extending the diagnosis engine.

## Boundaries
The prototype uses illustrative synthetic data unless a user uploads real data. It does not directly control hardware, connect to a live solar plant, or prove a physical fault. Statistical association is not causal proof.
