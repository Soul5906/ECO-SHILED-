# 8. Configuration, Security, and Limitations

## Local prototype defaults
- Frontend development URL: `http://localhost:5173`
- Backend URL: `http://127.0.0.1:8000`
- SQLite database: created by the backend under `backend/`
- CSV upload limit: 10 MB in the included API code.

## Configuration
The frontend reads `VITE_API_URL` when provided. For local use, the default backend URL is sufficient. For a different backend URL, create `frontend/.env.local` with:
```env
VITE_API_URL=http://127.0.0.1:8000
```
Restart Vite after changing environment variables.

## Security before public deployment
The prototype is intended for local development. Before exposing it publicly:
- Add authentication and role-based authorization.
- Use HTTPS.
- Restrict CORS to trusted origins.
- Add rate limiting and request monitoring.
- Add secure backups and database migrations.
- Define data-retention and deletion policies.
- Review privacy obligations for uploaded operational data.
- Do not expose detailed internal exceptions or secrets.

## Diagnostic limitations
- Demo data is synthetic.
- Rules are heuristic and incomplete.
- Ranking scores are not calibrated probabilities.
- Statistical outliers can be legitimate weather or operational events.
- The system does not establish causality.
- It is not a certified safety or maintenance alarm.
- Human review and site-specific validation are required before operational use.
