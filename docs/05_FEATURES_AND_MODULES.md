# 5. Features and Code Modules

## Main features
1. Overview dashboard.
2. Scenario selection.
3. CSV upload and validation.
4. Telemetry charts.
5. Data-quality checks.
6. Statistical anomaly detection.
7. Explainable root-cause ranking.
8. Next diagnostic test suggestions.
9. SQLite report history.
10. JSON report download.
11. CSV data export.
12. API health check and Swagger docs.

## Backend modules in the supplied prototype
- `backend/app/main.py`: API routes, scenario generation, persistence, upload/export handling.
- `backend/app/engine.py`: normalization, validation, anomaly screening, diagnosis logic, chart data.
- `backend/tests/test_engine.py`: basic engine tests.
- `backend/data/`: sample CSV files.

## Frontend modules
- `frontend/src/main.tsx`: React entry point.
- `frontend/src/App.tsx`: page state, API calls, tables, charts, upload, history and export actions.
- `frontend/src/styles.css`: responsive layout and styles.
- `frontend/package.json`: frontend dependencies and scripts.

## Extension suggestions
As the codebase grows, split `App.tsx` into page components, shared components, typed API services, hooks, and utilities. Split backend logic into route, schema, service, analysis, and storage modules. Add tests before changing diagnostic rules.
