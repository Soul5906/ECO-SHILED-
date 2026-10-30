# 6. API Guide

Base URL: `http://127.0.0.1:8000`

## Health
`GET /api/health`

Checks whether the backend is responding.

## Scenarios
`GET /api/scenarios`

Lists built-in demo scenarios.

`GET /api/scenarios/{scenario_id}`

Returns scenario metadata and rows. Available IDs in the prototype:
- `normal`
- `power-drop`
- `sensor-drift`
- `missing-telemetry`
- `cloud-passage`
- `duplicate-time`

## Analyze JSON rows
`POST /api/analyze`

Example body:
```json
{
  "source_name": "manual-example",
  "scenario_id": "normal",
  "rows": [
    {
      "timestamp": "2026-10-26T09:00:00",
      "power_kw": 12.1,
      "irradiance_wm2": 510,
      "temperature_c": 29.2,
      "inverter_id": "INV-01"
    }
  ]
}
```

The current engine requires enough well-formed data for meaningful analysis; validation errors are returned as HTTP 422.

## Analyze CSV
`POST /api/analyze-csv`

Use multipart form-data with the field name `file` and a `.csv` file.

## History
- `GET /api/history` — recent analysis IDs.
- `GET /api/history/{id}` — stored report.
- `GET /api/history/{id}/report` — JSON report download.
- `GET /api/history/{id}/csv` — input data CSV download.

## Interactive API docs
Open `http://127.0.0.1:8000/docs`.

## Note
This guide describes endpoints included in the prototype ZIP. Do not assume roadmap endpoints exist unless they have been implemented and tested.
