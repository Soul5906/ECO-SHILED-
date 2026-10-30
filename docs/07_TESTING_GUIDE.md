# 7. Testing Guide

## Backend tests
From the `backend` directory with the virtual environment active:
```powershell
pytest -q
```

## What the included tests cover
- A clean dataset receives a quality score of 100.
- Missing values are counted.
- Diagnosis returns hypotheses and limitations.

These are starter tests, not comprehensive verification of every feature.

## Manual smoke tests
1. Open `/api/health`.
2. Load each demo scenario.
3. Analyze a normal scenario.
4. Analyze a power-drop scenario.
5. Upload a valid CSV.
6. Upload a malformed CSV and confirm an understandable error.
7. Open report history.
8. Reopen a report.
9. Download JSON and CSV exports.
10. Restart the backend and check whether SQLite history persists.

## Add more automated tests
Add tests for missing columns, invalid timestamps, duplicate timestamps, zero variance, small datasets, extreme values, upload limits, unknown scenario IDs, API failures, report retrieval, and export content.

## Reporting results honestly
Record the exact command, date, environment, and pass/fail count. Do not write “all tests passed” unless the test command was actually run and passed.
