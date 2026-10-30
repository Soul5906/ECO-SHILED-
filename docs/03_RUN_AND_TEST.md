# 3. Running and Using the Website

## Start-up checklist
- [ ] Backend starts without a Python traceback.
- [ ] `http://127.0.0.1:8000/api/health` returns an OK response.
- [ ] Frontend starts using `npm run dev`.
- [ ] Browser opens the Vite local URL.
- [ ] Dashboard indicates the API is connected.

## First analysis
1. Open the website.
2. Choose a demo scenario.
3. Wait for the dataset to load.
4. Click **Analyze data**.
5. Open **Root-Cause Diagnosis**.
6. Read each hypothesis, evidence, caveats, and next test.
7. Open **Anomaly Detection** to inspect flagged observations.
8. Open **Reports** to revisit saved analyses.

## CSV upload
1. Prepare a CSV using the schema in `04_DATA_AND_CSV.md`.
2. Use the CSV upload control.
3. Review the analysis result and validation errors.
4. Download the report if needed.

## Export
- JSON: report data, analysis results, evidence, and limitations.
- CSV: input telemetry records.

## What counts as a successful prototype demo?
Demonstrate:
- One normal scenario.
- One scenario with an injected problem.
- Data-quality findings.
- A ranked diagnosis with evidence.
- A recommended next test.
- A saved report reopened from history.

Do not describe the prototype's heuristic score as a probability or present synthetic results as measurements from a real solar plant.
