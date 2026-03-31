# =============================================
# Stage 1: Build frontend
# =============================================
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --prefer-offline
COPY frontend/ ./
RUN npm run build

# =============================================
# Stage 2: Backend + static frontend
# =============================================
FROM python:3.13-slim AS production

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dépendances Python
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Code backend
COPY backend/ ./backend/
COPY frameworks/ ./frameworks/

# Frontend build statique
COPY --from=frontend-builder /app/frontend/.next ./frontend/.next
COPY --from=frontend-builder /app/frontend/public ./frontend/public
COPY --from=frontend-builder /app/frontend/package.json ./frontend/
COPY --from=frontend-builder /app/frontend/node_modules ./frontend/node_modules

# Répertoires
RUN mkdir -p /app/data /app/certs /app/instance

# Utilisateur non-root
RUN useradd -r -s /bin/false appuser && chown -R appuser:appuser /app
USER appuser

# Variables par défaut
ENV ENV=production \
    DATABASE_URL=postgresql://assistantaudit:changeme@db:5432/assistantaudit \
    LOG_LEVEL=INFO \
    PYTHONPATH=/app/backend

EXPOSE 8000

# Initialisation DB (create_all ou alembic upgrade selon l'état) + démarrage
CMD ["sh", "-c", "cd /app/backend && python docker_entrypoint.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
