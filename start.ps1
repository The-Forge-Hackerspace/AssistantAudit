# ============================================================
#  AssistantAudit — Script de démarrage (Windows PowerShell)
#  Gestion propre des processus avec arrêt fiable via Ctrl+C
# ============================================================
$ErrorActionPreference = "Stop"

$RootDir      = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir      = Join-Path $RootDir "venv"
$BackendDir   = Join-Path $RootDir "backend"
$FrontendDir  = Join-Path $RootDir "frontend"
$BackendPort  = 8000
$FrontendPort = 3000

# ── Mode dev (--dev = hot-reload, plus lent) ──
$DevMode = $false
if ($args -contains "--dev") { $DevMode = $true }

function Write-Log   { param($msg) Write-Host "[AssistantAudit] $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "[X] $msg" -ForegroundColor Red; exit 1 }

function Stop-PortProcess {
    param([int]$Port)
    $procIds = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $procIds) {
        try { taskkill /PID $p /T /F 2>$null | Out-Null } catch {}
    }
    # Attendre que le port soit libéré (max 10s)
    if ($procIds) {
        for ($w = 0; $w -lt 10; $w++) {
            $still = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
            if (-not $still) { break }
            Start-Sleep -Seconds 1
        }
    }
}

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

$pythonVersion = python --version 2>&1
$nodeVersion   = node --version 2>&1
Write-Ok $pythonVersion
Write-Ok "Node.js $nodeVersion"

if (Get-Command nmap -ErrorAction SilentlyContinue) {
    $nmapVersion = (nmap --version 2>&1) | Select-Object -First 1
    Write-Ok $nmapVersion
} else {
    Write-Warn "Nmap non trouve - le scanner reseau ne fonctionnera pas"
}

# ── PingCastle Setup ──
$PingCastleDir = Join-Path $RootDir "tools\pingcastle"
$PingCastleExe = Join-Path $PingCastleDir "PingCastle.exe"
$PingCastleRepo = "https://github.com/netwrix/pingcastle"

Write-Log "Verification de PingCastle..."

if (-not (Test-Path $PingCastleDir)) {
    Write-Log "Clonage du depot PingCastle..."
    if (Get-Command git -ErrorAction SilentlyContinue) {
        try {
            $toolsDir = Join-Path $RootDir "tools"
            if (-not (Test-Path $toolsDir)) {
                New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null
            }
            $cloneOutput = git clone --depth 1 $PingCastleRepo $PingCastleDir 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "PingCastle clone depuis GitHub"
            } else {
                Write-Warn "Impossible de cloner PingCastle"
                Write-Host $cloneOutput -ForegroundColor Yellow
                Write-Warn "Vous devrez installer PingCastle manuellement"
            }
        } catch {
            Write-Warn "Erreur lors du clonage de PingCastle : $_"
            Write-Warn "Vous devrez installer PingCastle manuellement"
        }
    } else {
        Write-Warn "Git non trouve - impossible de cloner PingCastle automatiquement"
        Write-Warn "Telechargez PingCastle depuis : https://github.com/netwrix/pingcastle/releases"
    }
} else {
    # Update existing PingCastle repository
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Push-Location $PingCastleDir
        try {
            $gitStatus = git status --porcelain 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Mise a jour de PingCastle..."
                $pullOutput = git pull --quiet origin master 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Ok "PingCastle mis a jour"
                } else {
                    Write-Warn "Impossible de mettre a jour PingCastle"
                    if ($pullOutput -and $pullOutput -ne "Already up to date.") {
                        Write-Host $pullOutput -ForegroundColor Yellow
                    }
                }
            }
        } catch {
            Write-Warn "Erreur lors de la mise a jour de PingCastle : $_"
        } finally {
            Pop-Location
        }
    }
}

# Check if PingCastle.exe exists and update .env
if (Test-Path $PingCastleExe) {
    Write-Ok "PingCastle.exe trouve : $PingCastleExe"
    
    # Update .env with PingCastle path
    $envFile = Join-Path $RootDir ".env"
    if (Test-Path $envFile) {
        $envContent = Get-Content $envFile -Raw
        if ($envContent -notmatch "PINGCASTLE_PATH=") {
            # Add PINGCASTLE_PATH if not present
            Add-Content -Path $envFile -Value "`nPINGCASTLE_PATH=$PingCastleExe"
            Write-Ok "PINGCASTLE_PATH configure dans .env"
        } else {
            # Update existing PINGCASTLE_PATH
            $envContent = $envContent -replace "PINGCASTLE_PATH=.*", "PINGCASTLE_PATH=$PingCastleExe"
            Set-Content -Path $envFile -Value $envContent -NoNewline
            Write-Ok "PINGCASTLE_PATH mis a jour dans .env"
        }
    }
} else {
    Write-Warn "PingCastle.exe non trouve dans $PingCastleDir"
    Write-Warn "Les fonctionnalites PingCastle ne seront pas disponibles"
    Write-Warn "Telechargez la derniere version : https://github.com/netwrix/pingcastle/releases"
}

# ── Environnement virtuel Python ──
if (-not (Test-Path $VenvDir)) {
    Write-Log "Creation de l'environnement virtuel Python..."
    python -m venv $VenvDir
    Write-Ok "venv cree dans $VenvDir"
}

& "$VenvDir\Scripts\Activate.ps1"
Write-Ok "venv active"

# ── Dépendances backend (skip si requirements.txt n'a pas changé) ──
$reqFile   = Join-Path $BackendDir "requirements.txt"
$stampFile = Join-Path $VenvDir ".deps_stamp"
$reqHash   = (Get-FileHash $reqFile -Algorithm MD5).Hash

if (-not (Test-Path $stampFile) -or (Get-Content $stampFile -ErrorAction SilentlyContinue) -ne $reqHash) {
    Write-Log "Installation des dependances backend..."
    pip install -q -r $reqFile
    $reqHash | Set-Content $stampFile
    Write-Ok "Dependances Python installees"
} else {
    Write-Ok "Dependances Python a jour (skip)"
}

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

# ── Nettoyage des ports (tuer les zombies) ──
Write-Log "Liberation des ports..."
Stop-PortProcess -Port $BackendPort
Stop-PortProcess -Port $FrontendPort
Start-Sleep -Milliseconds 500

# ── Démarrage backend ──
Write-Log "Demarrage du backend (port $BackendPort)..."
$backendArgs = "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$BackendPort", "--log-level", "info"
if ($DevMode) {
    $backendArgs += "--reload", "--reload-dir", "app"
    Write-Warn "Mode dev : hot-reload active (surveille app/ uniquement)"
}

$backendProc = Start-Process -FilePath "$VenvDir\Scripts\python.exe" `
    -ArgumentList $backendArgs `
    -WorkingDirectory $BackendDir `
    -WindowStyle Hidden `
    -PassThru

# Attendre que le backend soit prêt (max 45s en dev, 20s sinon)
$maxWait = if ($DevMode) { 45 } else { 20 }
Write-Log "Attente du backend (max ${maxWait}s)..."
$ready = $false
for ($i = 0; $i -lt $maxWait; $i++) {
    Start-Sleep -Seconds 1
    if ($backendProc.HasExited) {
        Write-Warn "Le backend a crashe au demarrage (code $($backendProc.ExitCode))."
        Write-Warn "Verifiez backend/logs/assistantaudit.log pour les details."
        break
    }
    try {
        $code = curl.exe -s -o NUL -w "%{http_code}" "http://localhost:${BackendPort}/api/v1/health" 2>$null
        if ($code -eq "200") { $ready = $true; break }
    } catch { }
    # Afficher un point de progression toutes les 5s
    if ($i -gt 0 -and $i % 5 -eq 0) { Write-Host "  ... ${i}s" -ForegroundColor DarkGray }
}

if ($ready) {
    Write-Ok "Backend pret sur http://localhost:$BackendPort (${i}s)"
} elseif (-not $backendProc.HasExited) {
    Write-Warn "Le backend met du temps a demarrer..."
}

# ── Démarrage frontend (via cmd.exe pour éviter l'ouverture de npx.ps1) ──
Write-Log "Demarrage du frontend (port $FrontendPort)..."
$frontendProc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npx next dev --port $FrontendPort" `
    -WorkingDirectory $FrontendDir `
    -WindowStyle Hidden `
    -PassThru

Start-Sleep -Seconds 2

# ── Récapitulatif ──
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║           Tout est pret !                    ║" -ForegroundColor Green
Write-Host "  ╠══════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "  ║  Frontend  : http://localhost:$FrontendPort           ║" -ForegroundColor Green
Write-Host "  ║  API       : http://localhost:$BackendPort           ║" -ForegroundColor Green
Write-Host "  ║  Swagger   : http://localhost:$BackendPort/docs      ║" -ForegroundColor Green
Write-Host "  ║  Login     : admin / Admin@2026!             ║" -ForegroundColor Green
if ($DevMode) {
Write-Host "  ║  Mode      : dev (hot-reload actif)          ║" -ForegroundColor Yellow
}
Write-Host "  ╠══════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "  ║  Ctrl+C pour arreter les services            ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# ── Boucle de surveillance avec arrêt propre ──
try {
    Write-Log "Services en cours d'execution... (Ctrl+C pour arreter)"
    while ($true) {
        # Auto-restart si un processus crash
        if ($backendProc.HasExited) {
            Write-Warn "Le backend s'est arrete (code $($backendProc.ExitCode)). Redemarrage..."
            $backendProc = Start-Process -FilePath "$VenvDir\Scripts\python.exe" `
                -ArgumentList $backendArgs `
                -WorkingDirectory $BackendDir `
                -WindowStyle Hidden `
                -PassThru
        }
        if ($frontendProc.HasExited) {
            Write-Warn "Le frontend s'est arrete (code $($frontendProc.ExitCode)). Redemarrage..."
            $frontendProc = Start-Process -FilePath "cmd.exe" `
                -ArgumentList "/c", "npx next dev --port $FrontendPort" `
                -WorkingDirectory $FrontendDir `
                -WindowStyle Hidden `
                -PassThru
        }
        Start-Sleep -Seconds 3
    }
} finally {
    Write-Host ""
    Write-Log "Arret des services..."

    # taskkill /T = tree kill (tue le processus ET tous ses enfants)
    if (-not $backendProc.HasExited) {
        try { taskkill /PID $backendProc.Id /T /F 2>$null | Out-Null } catch {}
    }
    if (-not $frontendProc.HasExited) {
        try { taskkill /PID $frontendProc.Id /T /F 2>$null | Out-Null } catch {}
    }

    # Nettoyage final des ports (sécurité)
    Start-Sleep -Milliseconds 500
    Stop-PortProcess -Port $BackendPort
    Stop-PortProcess -Port $FrontendPort

    Write-Ok "Tous les services sont arretes proprement."
}
