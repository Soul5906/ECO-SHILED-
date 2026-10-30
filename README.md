# ECO-SHIELD — Project Guide

Welcome to ECO-SHIELD, an evidence-driven clean-energy diagnostics prototype. Start here if you are new to the project.

## What does it do?
- Loads synthetic solar telemetry scenarios or user CSV data.
- Checks data quality.
- Flags statistical outliers.
- Ranks possible diagnostic explanations with evidence and caveats.
- Suggests next diagnostic checks.
- Saves analysis history and exports reports.

## Read the guides in this order
1. `docs/01_PROJECT_OVERVIEW.md` — what the project does and how it works.
2. `docs/ECO_SHIELD_Full_Research_Paper.pdf` (and `.md`) — peer-review-grade research paper.
3. `docs/ECO_SHIELD_Presentation_Deck_and_Summary.pdf` (and `.md`) — complete 12-slide pitch deck and executive summary.
4. `docs/02_INSTALLATION_WINDOWS.md` — install and run on Windows 11.
5. `docs/03_RUN_AND_TEST.md` — run the website, test features, and troubleshoot.
6. `docs/04_DATA_AND_CSV.md` — data format and upload rules.
7. `docs/05_FEATURES_AND_MODULES.md` — features and code responsibilities.
8. `docs/06_API_GUIDE.md` — backend API endpoints.
9. `docs/07_TESTING_GUIDE.md` — automated tests.
10. `docs/08_CONFIGURATION_AND_SECURITY.md` — settings, limitations, and deployment cautions.
11. `docs/DEPLOYMENT_GUIDE.md` — complete production deployment guide (Render, Docker, Vercel, Windows/Linux).
12. `docs/DECOUPLED_VERCEL_RENDER_DEPLOYMENT.md` — step-by-step Vercel + Render decoupled deployment guide.
13. `docs/09_DEVELOPMENT_ROADMAP.md` — suggested implementation order and future enhancements.

## Quick start
This pack documents the project; it does not replace the source-code ZIP.

### Backend terminal
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend terminal
```powershell
cd frontend
npm install
npm run dev
```
Open the local URL printed by Vite, commonly `http://localhost:5173`.

Backend docs: `http://127.0.0.1:8000/docs`

## Requirements
- Python 3.10 or newer
- Node.js 18 or newer (20+ recommended)
- VS Code or another editor
- Internet access for installing packages

## Important note
This is a prototype, not a certified plant-monitoring or safety system. Diagnosis scores are heuristic rankings, not calibrated probabilities. Validate all results before using them operationally.
