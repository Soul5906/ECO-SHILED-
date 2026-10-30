# ==============================================================================
# ECO-SHIELD Multi-Stage Production Dockerfile
# Stage 1: Build React + TypeScript Frontend
# Stage 2: Lightweight Python Backend Serving API & Static Assets
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Frontend Build
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /build

# Install dependencies with clean cache
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source and build production bundle
COPY frontend/ ./
ENV VITE_API_BASE_URL=/api
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Production Python Backend
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS production

# Set environment defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    FRONTEND_DIST_DIR=/app/frontend/dist \
    DATABASE_URL=sqlite:////data/ecoshield.db

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir reportlab pillow

# Copy backend application code
COPY backend/ ./

# Copy built frontend dist from Stage 1
COPY --from=frontend-builder /build/dist /app/frontend/dist

# Create persistent data volume for SQLite
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Start Uvicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
