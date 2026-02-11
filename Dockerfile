# ---- Build Stage ----
FROM python:3.12-slim AS base

WORKDIR /app

# Dépendances système (nmap pour les scans)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code applicatif
COPY backend/ ./backend/
COPY frameworks/ ./frameworks/

# Répertoires de données
RUN mkdir -p backend/instance backend/uploads backend/logs

WORKDIR /app/backend

# Port
EXPOSE 8000

# Démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
