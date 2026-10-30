# 4. Data and CSV Guide

## Required columns
| Column | Meaning | Example |
|---|---|---|
| `timestamp` | Reading time | `2026-10-26T09:00:00` |
| `power_kw` | Power output in kilowatts | `12.1` |
| `irradiance_wm2` | Irradiance in watts per square metre | `510` |
| `temperature_c` | Temperature in Celsius | `29.2` |

Optional column: `inverter_id`.

## Example
```csv
timestamp,power_kw,irradiance_wm2,temperature_c,inverter_id
2026-10-26T09:00:00,12.1,510,29.2,INV-01
2026-10-26T09:10:00,13.0,545,30.0,INV-01
2026-10-26T09:20:00,14.2,580,31.1,INV-01
2026-10-26T09:30:00,15.0,610,31.8,INV-01
2026-10-26T09:40:00,15.7,635,32.2,INV-01
```

## Rules
- Use a header row.
- Use consistent units for the same column.
- Use parseable timestamps.
- Use numeric values for numeric fields.
- Leave unavailable values blank; do not replace missing values with zero.
- Avoid mixing local times and UTC without a documented timezone.
- Keep the original source file as a backup.
- Use one row per measurement interval where possible.

## Common validation issues
- Missing required columns.
- Blank numeric cells.
- Unparseable timestamps.
- Duplicate timestamps.
- Negative power or irradiance.
- Implausible temperature values.
- Incorrect decimal separators or units.

## Data privacy
Use synthetic or authorized data for demonstrations. Do not upload confidential site telemetry to a public service without permission.
