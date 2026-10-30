# ECO-SHIELD: Production Deployment Guide

This guide covers all options for deploying ECO-SHIELD to production:
1. **[Method 1: Free 1-Click Cloud Hosting (Render.com)](#method-1-free-1-click-cloud-hosting-on-rendercom)** *(Recommended for Hackathons & Demos)*
2. **[Method 2: Docker & Docker Compose](#method-2-docker--docker-compose-any-vps-or-cloud-vm)** *(Recommended for Cloud VPS / On-Premise)*
3. **[Method 3: Decoupled Deploy (Vercel Frontend + Render Backend)](#method-3-decoupled-deployment-vercel--render)**
4. **[Method 4: Local / Self-Hosted Production Server](#method-4-local--self-hosted-production-server-windows--linux)**
5. **[Environment Variables & Configuration](#environment-variables--configuration)**

---

## Architecture of Deployed ECO-SHIELD

ECO-SHIELD can be deployed as a **unified single-service architecture**:
- **API routes** run at `/api/*`
- **OpenAPI Swagger documentation** runs at `/docs`
- **React 18 + TypeScript SPA** is served directly from `/`

```
User Browser
    │
    ▼
[ port 8000 / $PORT ]
├── /api/*          ──> FastAPI Diagnostic Router
├── /docs           ──> Swagger Interactive API
└── /* (Catch-all)  ──> React SPA (frontend/dist/index.html)
```
*(No separate frontend server is required in production!)*

---

## Method 1: Free 1-Click Cloud Hosting on Render.com

[Render.com](https://render.com) offers a free tier supporting Docker web services.

### Steps to Deploy:
1. **Push your code to a GitHub or GitLab repository:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit of ECO-SHIELD"
   git remote add origin https://github.com/<your-username>/ECO_SHIELD.git
   git push -u origin main
   ```
2. **Log into [Render.com](https://dashboard.render.com):**
   - Click **New +** -> **Blueprint**.
   - Connect your GitHub repository.
   - Render will automatically detect the provided [`render.yaml`](file:///d:/ECO-SHIELD%20Hackathon%20Deck/ECO_SHIELD/render.yaml) file!
3. **Click "Apply":**
   - Render will build the multi-stage [`Dockerfile`](file:///d:/ECO-SHIELD%20Hackathon%20Deck/ECO_SHIELD/Dockerfile), compile the React frontend, set up Python, and launch the service.
4. **Your Live URL:**
   - Within 3–5 minutes, you will receive a public HTTPS URL (e.g., `https://eco-shield.onrender.com`).
   - Visiting the URL opens the full interactive dashboard; API docs are at `https://eco-shield.onrender.com/docs`.

---

## Method 2: Docker & Docker Compose (Any VPS or Cloud VM)

Deploying to any cloud server (DigitalOcean, AWS EC2, Hetzner, GCP Compute Engine, Linode):

### Prerequisites:
- Docker Engine & Docker Compose installed.

### Deploy Steps:
1. Clone or copy the project to your server:
   ```bash
   git clone <your-repo-url>
   cd ECO_SHIELD
   ```
2. Build and run in background mode:
   ```bash
   docker compose up -d --build
   ```
3. Verify status:
   ```bash
   docker compose ps
   curl http://localhost:8000/api/health
   ```
4. Access the application:
   - Dashboard: `http://<your-server-ip>:8000`
   - API Docs: `http://<your-server-ip>:8000/docs`
   - The SQLite database (`ecoshield.db`) persists in the Docker volume named `ecoshield_sqlite_data`.

---

## Method 3: Decoupled Deployment (Vercel + Render)

If you prefer hosting the React frontend on **Vercel** and the backend on **Render** or **Railway**:

### Step 3A: Deploy Backend to Render or Railway
1. In Render, create a **Web Service** from your Git repo.
2. Set Root Directory: `backend`.
3. Build Command: `pip install -r requirements.txt reportlab pillow`.
4. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Set Environment Variable:
   - `CORS_ORIGINS`: `https://your-frontend-domain.vercel.app`
6. Note your backend URL (e.g. `https://ecoshield-backend.onrender.com`).

### Step 3B: Deploy Frontend to Vercel
1. Import the `frontend` folder into [Vercel](https://vercel.com).
2. Set Framework Preset: **Vite**.
3. Add Environment Variable in Vercel project settings:
   - `VITE_API_BASE_URL`: `https://ecoshield-backend.onrender.com/api`
4. Deploy! Vercel will handle global CDN caching and automatic SSL.

---

## Method 4: Local / Self-Hosted Production Server (Windows & Linux)

To run a production-optimized build on your own workstation or local server:

### On Windows 11 / 10:
Double-click [`deploy_windows.bat`](file:///d:/ECO-SHIELD%20Hackathon%20Deck/ECO_SHIELD/deploy_windows.bat) or run from PowerShell:
```powershell
.\deploy_windows.bat
```
*What this script does:*
1. Compiles the React frontend using `npm run build`.
2. Verifies Python dependencies.
3. Launches the unified Uvicorn server on `http://localhost:8000`.
4. Opens your default web browser to the dashboard.

### On Linux / macOS:
```bash
chmod +x deploy_linux.sh
./deploy_linux.sh
```

---

## Environment Variables & Configuration

Configure these via environment variables or `.env` in the backend:

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | Port for the Uvicorn server (automatically assigned on Render/Railway/Fly.io) |
| `HOST` | `0.0.0.0` | Network binding interface |
| `DEBUG` | `false` | Enable/disable debug logging |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `DATABASE_URL` | `sqlite:///./ecoshield.db` | SQLite database URI |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed origins or `*` for all |
| `FRONTEND_DIST_DIR` | `../frontend/dist` | Directory containing built React assets |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum CSV upload file size |
| `MAX_ROWS` | `100000` | Maximum rows allowed per telemetry dataset |

---

## Production Security & Best Practices

1. **Keep Diagnostic Boundaries Clear:** ECO-SHIELD is an advisory decision-support system. It must not be directly connected to hardware actuators without human verification.
2. **Reverse Proxy (Nginx / Caddy):** For public servers, put Nginx or Caddy in front of port 8000 to manage Let's Encrypt SSL certificates automatically.
3. **Database Backups:** The SQLite database `ecoshield.db` contains historical audit trails. Back up this single file periodically.
