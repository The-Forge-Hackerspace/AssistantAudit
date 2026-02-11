# ============================================================
#  AssistantAudit — Script de démarrage (Windows PowerShell)
# ============================================================
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $RootDir "venv"
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$BackendPort = 8000
$FrontendPort = 3000

function Write-Log   { param($msg) Write-Host "[AssistantAudit] $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "[X] $msg" -ForegroundColor Red; exit 1 }

# ── En-tête ──
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║         AssistantAudit v2.0.0                ║" -ForegroundColor Cyan
Write-Host "  ║     Plateforme d'audit d'infrastructure IT   ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Vérification des prérequis ──
Write-Log "Verification des prerequis..."

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Fail "Python 3 requis. Installez-le : https://python.org"
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Fail "Node.js requis. Installez-le : https://nodejs.org"
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Fail "npm requis."
}

$pythonVersion = python --version 2>&1
$nodeVersion = node --version 2>&1
Write-Ok $pythonVersion
Write-Ok "Node.js $nodeVersion"

if (Get-Command nmap -ErrorAction SilentlyContinue) {
    $nmapVersion = (nmap --version 2>&1) | Select-Object -First 1
    Write-Ok $nmapVersion
} else {
    Write-Warn "Nmap non trouve - le scanner reseau ne fonctionnera pas"
}

# ── Environnement virtuel Python ──
if (-not (Test-Path $VenvDir)) {
    Write-Log "Creation de l'environnement virtuel Python..."
    python -m venv $VenvDir
    Write-Ok "venv cree dans $VenvDir"
}

& "$VenvDir\Scripts\Activate.ps1"
Write-Ok "venv active"

# ── Dépendances backend ──
Write-Log "Installation des dependances backend..."
pip install -q -r "$BackendDir\requirements.txt"
Write-Ok "Dependances Python installees"

# ── Initialisation BDD ──
$dbPath = Join-Path $BackendDir "instance\assistantaudit.db"
if (-not (Test-Path $dbPath)) {
    Write-Log "Premiere execution - initialisation de la base de donnees..."
    Push-Location $BackendDir
    python init_db.py
    Pop-Location
    Write-Ok "Base de donnees initialisee (admin / Admin@2026!)"
} else {
    Write-Ok "Base de donnees existante detectee"
}

# ── Migrations Alembic ──
Write-Log "Application des migrations..."
Push-Location $BackendDir
try {
    python -m alembic upgrade head 2>$null
    Write-Ok "Migrations appliquees"
} catch {
    Write-Warn "Migrations deja a jour"
}
Pop-Location

# ── Dépendances frontend ──
$nodeModules = Join-Path $FrontendDir "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Log "Installation des dependances frontend..."
    Push-Location $FrontendDir
    npm install --silent
    Pop-Location
    Write-Ok "Dependances Node.js installees"
} else {
    Write-Ok "node_modules existant"
}

# ── Démarrage backend ──
Write-Log "Demarrage du backend (port $BackendPort)..."
$backendJob = Start-Job -ScriptBlock {
    param($root, $venv, $port)
    Set-Location $root
    & "$venv\Scripts\python.exe" -m uvicorn backend.app.main:app `
        --host 0.0.0.0 `
        --port $port `
        --reload `
        --log-level info
} -ArgumentList $RootDir, $VenvDir, $BackendPort

# Attendre que le backend soit prêt
Write-Log "Attente du backend..."
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$BackendPort/api/v1/health" -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch { }
}

if ($ready) {
    Write-Ok "Backend pret sur http://localhost:$BackendPort"
} else {
    Write-Warn "Le backend met du temps a demarrer, il sera bientot pret..."
}

# ── Démarrage frontend ──
Write-Log "Demarrage du frontend (port $FrontendPort)..."
$frontendJob = Start-Job -ScriptBlock {
    param($frontDir, $port)
    Set-Location $frontDir
    npx next dev --port $port
} -ArgumentList $FrontendDir, $FrontendPort

Start-Sleep -Seconds 3

# ── Récapitulatif ──
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║           Tout est pret !                    ║" -ForegroundColor Green
Write-Host "  ╠══════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "  ║  Frontend  : http://localhost:$FrontendPort          ║" -ForegroundColor Green
Write-Host "  ║  API       : http://localhost:$BackendPort           ║" -ForegroundColor Green
Write-Host "  ║  Swagger   : http://localhost:$BackendPort/docs      ║" -ForegroundColor Green
Write-Host "  ║  Login     : admin / Admin@2026!             ║" -ForegroundColor Green
Write-Host "  ╠══════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "  ║  Ctrl+C pour arreter les services            ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# ── Garder le script en vie ──
try {
    Write-Log "Services en cours d'execution... (Ctrl+C pour arreter)"
    while ($true) {
        # Vérifier que les jobs tournent
        if ($backendJob.State -eq "Failed") {
            Write-Warn "Le backend s'est arrete. Logs :"
            Receive-Job $backendJob
        }
        if ($frontendJob.State -eq "Failed") {
            Write-Warn "Le frontend s'est arrete. Logs :"
            Receive-Job $frontendJob
        }
        Start-Sleep -Seconds 5
    }
} finally {
    Write-Log "Arret des services..."
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Stop-Job $frontendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $frontendJob -ErrorAction SilentlyContinue
    Write-Ok "Services arretes."
}
