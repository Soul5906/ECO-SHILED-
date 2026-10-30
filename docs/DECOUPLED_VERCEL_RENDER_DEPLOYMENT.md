# ECO-SHIELD: Decoupled Deployment Walkthrough (Vercel + Render / Railway)

This guide walks you through deploying ECO-SHIELD as a modern decoupled web application:
- **Frontend:** Hosted on **Vercel** (Global Edge CDN, instantaneous builds, automatic SSL).
- **Backend API:** Hosted on **Render** or **Railway** (FastAPI Python service, SQLite persistence, automatic SSL).

```
   ┌─────────────────────────────────────────────────────────┐
   │                     USER BROWSER                        │
   └────────────────────────────┬────────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
        ▼ (Loads UI Assets)                             ▼ (API Calls / JSON / Reports)
┌───────────────────────────────┐               ┌───────────────────────────────┐
│        VERCEL (CDN)           │               │     RENDER / RAILWAY          │
│  React + TypeScript + Vite    │               │     FastAPI + Python 3.11     │
│  https://<your-app>.vercel.app│──────────────>│  https://<backend>.onrender...│
└───────────────────────────────┘               └───────────────┬───────────────┘
                                                                │
                                                                ▼
                                                ┌───────────────────────────────┐
                                                │     SQLite (ecoshield.db)     │
                                                │   Audit Logs & History        │
                                                └───────────────────────────────┘
```

---

## Step 1: Push Your Code to GitHub

If you haven't already pushed this repository to GitHub:

1. Open your terminal in the project root (`d:\ECO-SHIELD Hackathon Deck\ECO_SHIELD`).
2. Run the following commands:
   ```bash
   git init
   git add .
   git commit -m "feat: complete ECO-SHIELD project with deployment configurations"
   git branch -M main
   ```
3. Create a new repository on [GitHub.com](https://github.com/new) (named `ECO_SHIELD`).
4. Link and push your repository:
   ```bash
   git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/ECO_SHIELD.git
   git push -u origin main
   ```

---

## Step 2: Deploy Backend to Render (Free Tier)

> *Tip: You can also use [Railway.app](https://railway.app), which follows identical build and start commands.*

1. **Log in to [Render Dashboard](https://dashboard.render.com).**
2. Click **New +** (top right) and select **Web Service**.
3. Select **Build and deploy from a Git repository** and connect your `ECO_SHIELD` repository.
4. Fill in the deployment settings:
   - **Name:** `ecoshield-backend` (or your preferred name)
   - **Region:** Choose the region closest to you (e.g., *Oregon (US West)* or *Frankfurt (EU)*)
   - **Branch:** `main`
   - **Root Directory:** `backend` *(⚠️ Important: Type `backend` here)*
   - **Runtime:** `Python 3`
   - **Build Command:**
     ```bash
     pip install -r requirements.txt reportlab pillow
     ```
   - **Start Command:**
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type:** `Free`
5. **Add Environment Variables (under "Advanced" or "Environment Variables"):**
   - Click **Add Environment Variable** for each:

   | Key | Value | Note |
   |---|---|---|
   | `CORS_ORIGINS` | `*` | Allows your Vercel frontend domain to make API requests |
   | `DEBUG` | `false` | Production mode |
   | `LOG_LEVEL` | `INFO` | Standard logging |
   | `PYTHON_VERSION` | `3.11.9` | Ensures compatible Python runtime |

6. Click **Create Web Service**.
7. Render will build the backend (typically 1–2 minutes).
8. Once deployed, Render will display your live backend URL at the top:
   ```
   https://ecoshield-backend-xxxx.onrender.com
   ```
9. **Test Your Backend:**
   Open this URL in your browser:
   - `https://ecoshield-backend-xxxx.onrender.com/api/health` -> should return `{"status":"ok",...}`
   - `https://ecoshield-backend-xxxx.onrender.com/docs` -> should open the interactive Swagger API documentation.

---

## Step 3: Deploy Frontend to Vercel (Free Tier)

Now connect the React frontend to your live Render backend:

1. **Log in to [Vercel](https://vercel.com).**
2. Click **Add New...** -> **Project**.
3. Select your `ECO_SHIELD` GitHub repository and click **Import**.
4. In the **Configure Project** screen:
   - **Project Name:** `eco-shield` (or your preferred name)
   - **Framework Preset:** `Vite` (Vercel should auto-detect this)
   - **Root Directory:** Click **Edit** next to Root Directory and select `frontend`. *(⚠️ Important: Choose `frontend`)*
5. **Add Environment Variable:**
   Expand the **Environment Variables** section and add:
   - **Name:** `VITE_API_BASE_URL`
   - **Value:** `https://ecoshield-backend-xxxx.onrender.com/api`  
     *(Replace with your actual Render URL from Step 2, ensuring it ends with `/api`)*
6. Click **Deploy**.
7. Vercel will build and deploy the frontend in approximately 30–45 seconds.
8. Once finished, you will receive your live frontend URL:
   ```
   https://eco-shield-xxxx.vercel.app
   ```

---

## Step 4: Verify Your Full Decoupled Deployment

1. Open your live Vercel URL in your browser: `https://eco-shield-xxxx.vercel.app`.
2. **Test Scenario Diagnostics:**
   - Click the Scenario selector.
   - Select **"Gradual Power Decline"** or **"Cloud Passage Event"**.
   - Verify that the Recharts telemetry graphs render immediately and the Ranked Hypotheses load from the Render backend.
3. **Test CSV Upload:**
   - Upload any sample CSV file (from `backend/data/` or your own test file).
   - Verify validation issues, Q-Score computation, and anomaly records.
4. **Test Report Export:**
   - Click **Download Report** (JSON) or generate PDF report.
   - Verify that the analysis history is saved to the backend SQLite database.

---

## Troubleshooting & FAQ

### 1. "Cannot reach backend. Is the server running?"
- **Cause:** `VITE_API_BASE_URL` in Vercel is incorrect or Render free tier is waking up.
- **Fix:** On Render's free tier, servers spin down after 15 minutes of inactivity. The first request after sleep takes 30–45 seconds to wake up. Verify `VITE_API_BASE_URL` in Vercel Project Settings ends with `/api` and has no trailing slash (e.g. `https://your-backend.onrender.com/api`).

### 2. CORS Error in Browser Console (`Access-Control-Allow-Origin`)
- **Fix:** In your Render dashboard, check the `CORS_ORIGINS` environment variable. Set it to `*` or explicitly include your Vercel domain:
  ```
  CORS_ORIGINS=https://eco-shield-xxxx.vercel.app
  ```

### 3. Page Refresh Gives 404 on Sub-routes
- **Fix:** The included [`frontend/vercel.json`](file:///d:/ECO-SHIELD%20Hackathon%20Deck/ECO_SHIELD/frontend/vercel.json) already handles SPA routing rewrites to `/index.html`. Ensure `vercel.json` is located inside the `frontend/` directory.
