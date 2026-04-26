# =============================================
# Stage 1: Build frontend
# =============================================
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --prefer-offline
COPY frontend/ ./
RUN npm run build \
    && rm -rf node_modules/.cache

# =============================================
# Stage 2: Backend + static frontend
# =============================================
FROM python:3.13-slim-bookworm AS production

# Installer les dépendances système + WeasyPrint libs + PowerShell 7
# Tout dans une seule couche pour minimiser la taille de l'image
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq-dev gcc curl apt-transport-https \
       libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
       libffi-dev shared-mime-info \
    && curl -sSL https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb \
       -o /tmp/packages-microsoft-prod.deb \
    && dpkg -i /tmp/packages-microsoft-prod.deb \
    && rm /tmp/packages-microsoft-prod.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends powershell \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app

# Dépendances Python (gcc requis pour compiler les extensions C)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get update && apt-get purge -y --auto-remove gcc apt-transport-https \
    && rm -rf /var/lib/apt/lists/* \
    && find /usr/local/lib/python3.*/site-packages -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true

# Code backend
COPY backend/ ./backend/
COPY frameworks/ ./frameworks/

# Frontend build statique
COPY --from=frontend-builder /app/frontend/.next ./frontend/.next
COPY --from=frontend-builder /app/frontend/public ./frontend/public
COPY --from=frontend-builder /app/frontend/package.json ./frontend/
COPY --from=frontend-builder /app/frontend/node_modules ./frontend/node_modules

# Modules PowerShell requis par Monkey365
# On installe les sous-modules ciblés (évite ~2 Go pour Az et Microsoft.Graph complets)
RUN pwsh -NoProfile -Command "\
    Set-PSRepository PSGallery -InstallationPolicy Trusted; \
    Install-Module Az.Accounts                  -Scope AllUsers -Force -NoClobber; \
    Install-Module Az.Resources                 -Scope AllUsers -Force -NoClobber; \
    Install-Module ExchangeOnlineManagement     -Scope AllUsers -Force -NoClobber; \
    Install-Module MicrosoftTeams               -Scope AllUsers -Force -NoClobber; \
    Install-Module Microsoft.Graph.Authentication -Scope AllUsers -Force -NoClobber; \
    Install-Module Microsoft.Graph.Users        -Scope AllUsers -Force -NoClobber; \
    Install-Module PnP.PowerShell               -Scope AllUsers -Force -NoClobber \
    " \
    && rm -rf /root/.cache /tmp/* /var/tmp/* \
    && find /usr/local/share/powershell -name '*.nupkg' -delete 2>/dev/null; true

# Répertoires
RUN mkdir -p /app/data/blobs /app/certs /app/instance /app/tools/monkey365

# Utilisateur non-root
RUN useradd -r -s /bin/false appuser && chown -R appuser:appuser /app
USER appuser

# Variables par défaut
ENV ENV=production \
    DATABASE_URL=postgresql://assistantaudit:changeme@db:5432/assistantaudit \
    LOG_LEVEL=INFO \
    PYTHONPATH=/app/backend \
    FORWARDED_ALLOW_IPS=*

EXPOSE 8000

# Initialisation DB (create_all ou alembic upgrade selon l'etat) + demarrage.
# --proxy-headers : uvicorn honore X-Forwarded-Proto/For poses par le reverse
# proxy (NPMPlus en prod, Caddy en staging) -> request.url.scheme = "https"
# pour declencher HSTS, et X-Forwarded-For utilisable pour le rate-limit IP.
# --forwarded-allow-ips : par defaut '*' (port 8000 non publie via NPMPlus).
# A restreindre via FORWARDED_ALLOW_IPS=10.0.0.5 si le backend devient public.
CMD ["sh", "-c", "cd /app/backend && python docker_entrypoint.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=\"${FORWARDED_ALLOW_IPS:-*}\""]
