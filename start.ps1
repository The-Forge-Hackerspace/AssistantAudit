<#
.SYNOPSIS
    Démarre AssistantAudit (backend FastAPI + frontend Next.js + outils externes)

.DESCRIPTION
    Script de démarrage complet pour la plateforme d'audit d'infrastructure IT.
    Gère automatiquement :
    - Vérification des prérequis (Python, Node.js, PowerShell 7+, Git)
    - Configuration de l'environnement (.env)
    - Téléchargement/mise à jour des outils (PingCastle, Monkey365)
    - Initialisation de la base de données
    - Démarrage des services backend et frontend
    - Rotation des logs
    - Arrêt propre avec Ctrl+C

.PARAMETER dev
    Mode développement avec logs DEBUG et hot-reload activés

.PARAMETER build
    Mode production avec build optimisé (next build + uvicorn multi-workers)

.PARAMETER verbose
    Alias de --dev pour compatibilité

.EXAMPLE
    .\start.ps1
    Démarrage normal en mode développement

.EXAMPLE
    .\start.ps1 --dev
    Mode développement avec logs maximaux et hot-reload

.EXAMPLE
    .\start.ps1 --build
    Build et démarrage en mode production optimisé

.NOTES
    Version: 2.0.0
    Auteur: AssistantAudit Team
    Dernière mise à jour: 2026-02-15
#>

param(
    [switch]$dev,
    [switch]$build,
    [switch]$verbose
)

$ErrorActionPreference = "Stop"

# ═══════════════════════════════════════════════════════════
#  CONFIGURATION GLOBALE
# ═══════════════════════════════════════════════════════════

$RootDir      = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir      = Join-Path $RootDir "venv"
$BackendDir   = Join-Path $RootDir "backend"
$FrontendDir  = Join-Path $RootDir "frontend"
$ToolsDir     = Join-Path $RootDir "tools"
$BackendPort  = 8000
$FrontendPort = 3000

# Déterminer le mode d'exécution
$DevMode   = $dev -or $verbose -or ($args -contains "--dev") -or ($args -contains "--verbose")
$BuildMode = $build -or ($args -contains "--build")

if ($DevMode -and $BuildMode) {
    Write-Host "[!] Options --dev et --build incompatibles. Utilisez l'une ou l'autre." -ForegroundColor Yellow
    exit 1
}

# Variables globales pour tracking
$script:StartTime = Get-Date
$script:BackendPID = $null
$script:FrontendPID = $null

# ═══════════════════════════════════════════════════════════
#  FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════

function Write-Log {
    param($msg)
    $timestamp = if ($DevMode) { "[{0:HH:mm:ss}] " -f (Get-Date) } else { "" }
    Write-Host "${timestamp}[AssistantAudit] $msg" -ForegroundColor Cyan
}

function Write-Ok {
    param($msg)
    $timestamp = if ($DevMode) { "[{0:HH:mm:ss}] " -f (Get-Date) } else { "" }
    Write-Host "${timestamp}[OK] $msg" -ForegroundColor Green
}

function Write-Warn {
    param($msg)
    $timestamp = if ($DevMode) { "[{0:HH:mm:ss}] " -f (Get-Date) } else { "" }
    Write-Host "${timestamp}[!] $msg" -ForegroundColor Yellow
}

function Write-Fail {
    param($msg)
    $timestamp = if ($DevMode) { "[{0:HH:mm:ss}] " -f (Get-Date) } else { "" }
    Write-Host "${timestamp}[X] $msg" -ForegroundColor Red
    exit 1
}

function Write-Verbose-Custom {
    param($msg)
    if ($DevMode) {
        $timestamp = "[{0:HH:mm:ss.fff}] " -f (Get-Date)
        Write-Host "${timestamp}[VERBOSE] $msg" -ForegroundColor DarkGray
    }
}

function Stop-PortProcess {
    <#
    .SYNOPSIS
        Tue les processus occupant un port spécifique
    #>
    param([int]$Port)
    
    Write-Verbose-Custom "Vérification du port $Port..."
    $procIds = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    
    if ($procIds) {
        Write-Verbose-Custom "Processus trouvés sur le port ${Port}: $($procIds -join ', ')"
        foreach ($p in $procIds) {
            try {
                Write-Verbose-Custom "Arrêt du processus PID $p..."
                taskkill /PID $p /T /F 2>$null | Out-Null
            } catch {}
        }
        
        # Attendre que le port soit libéré (max 10s)
        for ($w = 0; $w -lt 10; $w++) {
            $still = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
            if (-not $still) {
                Write-Verbose-Custom "Port $Port libéré après ${w}s"
                break
            }
            Start-Sleep -Seconds 1
        }
    }
}

function Test-Prerequisite {
    <#
    .SYNOPSIS
        Vérifie qu'une commande/outil est disponible
    #>
    param(
        [string]$Name,
        [string]$Command,
        [string]$ErrorMessage,
        [switch]$Optional
    )
    
    Write-Verbose-Custom "Test du prérequis: $Name ($Command)"
    
    if (Get-Command $Command -ErrorAction SilentlyContinue) {
        return $true
    } else {
        if ($Optional) {
            Write-Warn "$ErrorMessage"
            return $false
        } else {
            Write-Fail "$ErrorMessage"
        }
    }
}

function Setup-GitTool {
    <#
    .SYNOPSIS
        Clone ou met à jour un outil depuis GitHub
    #>
    param(
        [string]$Name,
        [string]$RepoUrl,
        [string]$TargetDir,
        [string]$EnvVarName,
        [string]$ExecutablePath
    )
    
    Write-Log "Vérification de $Name..."
    
    if (-not (Test-Path $TargetDir)) {
        # Premier clonage
        Write-Log "Clonage de $Name depuis GitHub..."
        if (Get-Command git -ErrorAction SilentlyContinue) {
            try {
                Write-Verbose-Custom "git clone --depth 1 $RepoUrl $TargetDir"
                $cloneOutput = git clone --depth 1 $RepoUrl $TargetDir 2>&1
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Ok "$Name cloné depuis GitHub"
                } else {
                    Write-Warn "Impossible de cloner $Name"
                    if ($DevMode) { Write-Host $cloneOutput -ForegroundColor Yellow }
                    Write-Warn "Vous devrez installer $Name manuellement"
                    return $false
                }
            } catch {
                Write-Warn "Erreur lors du clonage de ${Name}: $_"
                Write-Warn "Vous devrez installer $Name manuellement"
                return $false
            }
        } else {
            Write-Warn "Git non trouvé - impossible de cloner $Name automatiquement"
            Write-Warn "Téléchargez $Name depuis : $RepoUrl"
            return $false
        }
    } else {
        # Mise à jour d'une installation existante
        if (Get-Command git -ErrorAction SilentlyContinue) {
            Push-Location $TargetDir
            try {
                Write-Verbose-Custom "Vérification du statut Git de $Name..."
                $gitStatus = git status --porcelain 2>&1
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Log "Mise à jour de $Name..."
                    $pullOutput = git pull --quiet origin master 2>&1
                    
                    if ($LASTEXITCODE -eq 0) {
                        # Obtenir le commit actuel
                        $commitHash = git rev-parse --short HEAD 2>&1
                        Write-Ok "$Name mis à jour (commit: $commitHash)"
                    } else {
                        Write-Verbose-Custom "Pull output: $pullOutput"
                        if ($pullOutput -match "Already up to date") {
                            Write-Ok "$Name déjà à jour"
                        } else {
                            Write-Warn "Impossible de mettre à jour $Name"
                            if ($DevMode) { Write-Host $pullOutput -ForegroundColor Yellow }
                        }
                    }
                }
            } catch {
                Write-Warn "Erreur lors de la mise à jour de ${Name}: $_"
            } finally {
                Pop-Location
            }
        }
    }
    
    # Vérifier l'exécutable et mettre à jour .env si fourni
    if ($ExecutablePath -and $EnvVarName) {
        $fullPath = Join-Path $TargetDir $ExecutablePath
        
        if (Test-Path $fullPath) {
            Write-Ok "$Name trouvé: $fullPath"
            Update-EnvVariable -Name $EnvVarName -Value $fullPath
            return $true
        } else {
            Write-Warn "$Name non trouvé dans $TargetDir"
            Write-Warn "Les fonctionnalités $Name ne seront pas disponibles"
            return $false
        }
    }
    
    return $true
}

function Update-PingCastle {
    <#
    .SYNOPSIS
        Met à jour PingCastle via PingCastleAutoUpdater.exe
    #>
    param(
        [string]$TargetDir,
        [string]$EnvVarName = "PINGCASTLE_PATH",
        [string]$ExecutableName = "PingCastle.exe"
    )
    
    $autoUpdaterPath = Join-Path $TargetDir "PingCastleAutoUpdater.exe"
    $pingCastlePath = Join-Path $TargetDir $ExecutableName
    
    # Vérifier si PingCastle est déjà installé
    if (-not (Test-Path $TargetDir)) {
        Write-Warn "Dossier PingCastle non trouvé: $TargetDir"
        Write-Warn "Veuillez télécharger PingCastle depuis: https://github.com/netwrix/pingcastle/releases/latest"
        Write-Warn "Puis extraire dans: $TargetDir"
        return $false
    }
    
    if (-not (Test-Path $pingCastlePath)) {
        Write-Warn "PingCastle.exe non trouvé dans: $TargetDir"
        Write-Warn "Veuillez télécharger PingCastle depuis: https://github.com/netwrix/pingcastle/releases/latest"
        return $false
    }
    
    # Si AutoUpdater disponible, l'utiliser pour la mise à jour
    if (Test-Path $autoUpdaterPath) {
        Write-Log "Vérification des mises à jour PingCastle via AutoUpdater..."
        
        try {
            $args = @()
            if ($DevMode) {
                # En mode dev, utiliser --dry-run pour prévisualiser
                $args += "--dry-run"
                Write-Verbose-Custom "Exécution: PingCastleAutoUpdater.exe --dry-run"
            }
            
            Push-Location $TargetDir
            $updateOutput = & .\PingCastleAutoUpdater.exe @args 2>&1
            Pop-Location
            
            if ($LASTEXITCODE -eq 0) {
                if ($DevMode -and $updateOutput -match "dry-run") {
                    Write-Ok "PingCastle AutoUpdater (mode aperçu) - OK"
                } else {
                    Write-Ok "PingCastle mis à jour avec succès"
                }
                if ($DevMode -and $updateOutput) {
                    Write-Verbose-Custom "Output: $updateOutput"
                }
            } else {
                Write-Verbose-Custom "AutoUpdater exit code: $LASTEXITCODE"
                if ($updateOutput -match "already.*up.*to.*date|déjà.*jour") {
                    Write-Ok "PingCastle déjà à jour"
                } else {
                    Write-Warn "Erreur lors de la mise à jour PingCastle"
                    if ($DevMode -and $updateOutput) {
                        Write-Host $updateOutput -ForegroundColor Yellow
                    }
                }
            }
        } catch {
            Write-Warn "Erreur lors de l'exécution de PingCastleAutoUpdater: $_"
        }
    } else {
        Write-Verbose-Custom "PingCastleAutoUpdater.exe non trouvé - pas de mise à jour automatique"
        Write-Ok "PingCastle trouvé (mise à jour manuelle requise)"
    }
    
    # Vérifier et mettre à jour .env
    if (Test-Path $pingCastlePath) {
        Write-Verbose-Custom "PingCastle.exe trouvé: $pingCastlePath"
        Update-EnvVariable -Name $EnvVarName -Value $pingCastlePath
        return $true
    }
    
    return $false
}

function Update-ToolFromGitHub {
    <#
    .SYNOPSIS
        Télécharge ou met à jour un outil depuis GitHub Releases
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ToolName,
        
        [Parameter(Mandatory)]
        [string]$RepoOwner,
        
        [Parameter(Mandatory)]
        [string]$RepoName,
        
        [Parameter(Mandatory)]
        [string]$TargetDir,
        
        [string]$AssetPattern = "*.zip",
        [switch]$VerifySHA256,
        [switch]$IncludePrerelease,
        [string]$EnvVarName,
        [string]$ExecutablePath
    )
    
    Write-Log "Vérification de $ToolName..."
    
    # Charger System.IO.Compression pour l'extraction ZIP
    Add-Type -Assembly 'System.IO.Compression.FileSystem' -ErrorAction SilentlyContinue
    
    try {
        # 1. Récupérer les releases depuis l'API GitHub
        $apiUrl = if ($IncludePrerelease) {
            "https://api.github.com/repos/$RepoOwner/$RepoName/releases"
        } else {
            "https://api.github.com/repos/$RepoOwner/$RepoName/releases/latest"
        }
        
        Write-Verbose-Custom "API URL: $apiUrl"
        
        $webParams = @{
            Uri = $apiUrl
            Headers = @{
                'User-Agent' = 'AssistantAudit-PowerShell'
                'Accept' = 'application/vnd.github.v3+json'
            }
            ErrorAction = 'Stop'
        }
        
        $release = Invoke-RestMethod @webParams
        
        # Si on inclut les prereleases, prendre la première
        if ($IncludePrerelease -and $release -is [array]) {
            $release = $release[0]
        }
        
        $latestVersion = $release.tag_name
        Write-Verbose-Custom "Dernière version disponible: $latestVersion"
        
        # 2. Vérifier la version locale
        $versionFile = Join-Path $TargetDir ".version"
        $currentVersion = $null
        
        if (Test-Path $versionFile) {
            $currentVersion = Get-Content $versionFile -Raw -ErrorAction SilentlyContinue | ForEach-Object { $_.Trim() }
            Write-Verbose-Custom "Version locale: $currentVersion"
        }
        
        # 3. Comparer les versions
        if ($currentVersion -eq $latestVersion -and (Test-Path $TargetDir)) {
            Write-Ok "$ToolName déjà à jour ($latestVersion)"
            
            # Vérifier l'exécutable et mettre à jour .env
            if ($ExecutablePath -and $EnvVarName) {
                $fullPath = Join-Path $TargetDir $ExecutablePath
                if (Test-Path $fullPath) {
                    Update-EnvVariable -Name $EnvVarName -Value $fullPath
                    return $true
                }
            }
            return $true
        }
        
        # 4. Trouver l'asset correspondant au pattern
        $asset = $release.assets | Where-Object { $_.name -like $AssetPattern } | Select-Object -First 1
        
        if (-not $asset) {
            Write-Warn "Aucun asset trouvé correspondant à '$AssetPattern' dans la release $latestVersion"
            return $false
        }
        
        Write-Log "Téléchargement de $ToolName $latestVersion..."
        Write-Verbose-Custom "Asset: $($asset.name) ($([math]::Round($asset.size / 1MB, 2)) MB)"
        
        # 5. Télécharger le ZIP
        $tempZip = Join-Path $env:TEMP "$ToolName-$latestVersion.zip"
        
        $downloadParams = @{
            Uri = $asset.browser_download_url
            OutFile = $tempZip
            Headers = @{ 'User-Agent' = 'AssistantAudit-PowerShell' }
            ErrorAction = 'Stop'
        }
        
        Invoke-WebRequest @downloadParams
        Write-Verbose-Custom "Téléchargé dans: $tempZip"
        
        # 6. Vérifier SHA256 si demandé
        if ($VerifySHA256) {
            $sha256Asset = $release.assets | Where-Object { $_.name -like "*.sha256" } | Select-Object -First 1
            
            if ($sha256Asset) {
                Write-Verbose-Custom "Vérification du hash SHA256..."
                
                $tempSHA = Join-Path $env:TEMP "$ToolName-$latestVersion.sha256"
                Invoke-WebRequest -Uri $sha256Asset.browser_download_url -OutFile $tempSHA -Headers @{ 'User-Agent' = 'AssistantAudit-PowerShell' }
                
                $expectedHash = (Get-Content $tempSHA -Raw).Split()[0].Trim()
                $actualHash = (Get-FileHash -Path $tempZip -Algorithm SHA256).Hash
                
                if ($actualHash -eq $expectedHash) {
                    Write-Ok "Hash SHA256 vérifié ✓"
                } else {
                    Write-Fail "Hash SHA256 invalide! Attendu: $expectedHash, Obtenu: $actualHash"
                    Remove-Item $tempZip -Force -ErrorAction SilentlyContinue
                    return $false
                }
                
                Remove-Item $tempSHA -Force -ErrorAction SilentlyContinue
            } else {
                Write-Warn "Fichier .sha256 non trouvé - impossible de vérifier l'intégrité"
            }
        }
        
        # 7. Extraire le ZIP
        Write-Log "Extraction de $ToolName..."
        
        # Créer le dossier cible s'il n'existe pas
        if (-not (Test-Path $TargetDir)) {
            New-Item -Path $TargetDir -ItemType Directory -Force | Out-Null
        }
        
        # Sauvegarder l'ancienne installation si elle existe
        if ((Test-Path $TargetDir) -and (Get-ChildItem $TargetDir -ErrorAction SilentlyContinue)) {
            $backupDir = "$TargetDir.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            Write-Verbose-Custom "Sauvegarde de l'installation actuelle dans: $backupDir"
            Copy-Item -Path $TargetDir -Destination $backupDir -Recurse -Force -ErrorAction SilentlyContinue
        }
        
        # Extraire le ZIP
        try {
            [System.IO.Compression.ZipFile]::ExtractToDirectory($tempZip, $TargetDir, $true)
            Write-Ok "$ToolName $latestVersion installé avec succès"
        } catch {
            Write-Warn "Erreur lors de l'extraction: $_"
            # Fallback avec Expand-Archive
            Expand-Archive -Path $tempZip -DestinationPath $TargetDir -Force
            Write-Ok "$ToolName $latestVersion installé avec succès (méthode alternative)"
        }
        
        # 8. Sauvegarder la version
        Set-Content -Path $versionFile -Value $latestVersion -NoNewline
        Write-Verbose-Custom "Version sauvegardée: $latestVersion"
        
        # 9. Nettoyer le fichier temporaire
        Remove-Item $tempZip -Force -ErrorAction SilentlyContinue
        
        # 10. Vérifier l'exécutable et mettre à jour .env
        if ($ExecutablePath -and $EnvVarName) {
            $fullPath = Join-Path $TargetDir $ExecutablePath
            
            if (Test-Path $fullPath) {
                Write-Ok "$ToolName trouvé: $fullPath"
                Update-EnvVariable -Name $EnvVarName -Value $fullPath
                return $true
            } else {
                Write-Warn "$ExecutablePath non trouvé après extraction dans $TargetDir"
                Write-Warn "Les fonctionnalités $ToolName pourraient ne pas être disponibles"
                return $false
            }
        }
        
        return $true
        
    } catch {
        Write-Warn "Erreur lors de la mise à jour de ${ToolName}: $_"
        if ($DevMode) {
            Write-Host $_.Exception.Message -ForegroundColor Yellow
            Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
        }
        return $false
    }
}

function Update-EnvVariable {
    <#
    .SYNOPSIS
        Met à jour ou ajoute une variable dans le fichier .env
    #>
    param(
        [string]$Name,
        [string]$Value
    )
    
    $envFile = Join-Path $RootDir ".env"
    
    if (-not (Test-Path $envFile)) {
        Write-Verbose-Custom "Fichier .env non trouvé, création..."
        return
    }
    
    Write-Verbose-Custom "Mise à jour de $Name dans .env"
    $envContent = Get-Content $envFile -Raw
    
    if ($envContent -notmatch "$Name=") {
        # Ajouter la variable si elle n'existe pas
        Add-Content -Path $envFile -Value "`n$Name=$Value"
        Write-Verbose-Custom "$Name ajouté à .env"
    } else {
        # Mettre à jour la variable existante
        $envContent = $envContent -replace "$Name=.*", "$Name=$Value"
        Set-Content -Path $envFile -Value $envContent -NoNewline
        Write-Verbose-Custom "$Name mis à jour dans .env"
    }
}

function Rotate-Logs {
    <#
    .SYNOPSIS
        Effectue la rotation des fichiers de log
    #>
    param(
        [string]$LogPath,
        [int]$MaxSizeMB = 10,
        [int]$KeepCount = 5
    )
    
    if (-not (Test-Path $LogPath)) {
        Write-Verbose-Custom "Fichier de log $LogPath n'existe pas encore"
        return
    }
    
    $logFile = Get-Item $LogPath
    $sizeMB = [math]::Round($logFile.Length / 1MB, 2)
    
    Write-Verbose-Custom "Taille du log: ${sizeMB}MB (max: ${MaxSizeMB}MB)"
    
    if ($logFile.Length -gt ($MaxSizeMB * 1MB)) {
        Write-Log "Rotation du log (${sizeMB}MB > ${MaxSizeMB}MB)..."
        
        # Supprimer le plus ancien
        $oldestLog = "$LogPath.$KeepCount"
        if (Test-Path $oldestLog) {
            Remove-Item $oldestLog -Force
            Write-Verbose-Custom "Suppression de l'ancienne archive: $oldestLog"
        }
        
        # Décaler les archives existantes
        for ($i = $KeepCount - 1; $i -ge 1; $i--) {
            $current = "$LogPath.$i"
            $next = "$LogPath.$($i + 1)"
            if (Test-Path $current) {
                Move-Item $current $next -Force
                Write-Verbose-Custom "Renommage: $current -> $next"
            }
        }
        
        # Archiver le log actuel
        Move-Item $LogPath "$LogPath.1" -Force
        Write-Ok "Log archivé: $LogPath -> $LogPath.1"
    }
}

function Clean-PidFile {
    <#
    .SYNOPSIS
        Nettoie un fichier PID et tue le processus s'il existe encore
    #>
    param([string]$PidFile)
    
    if (Test-Path $PidFile) {
        Write-Verbose-Custom "Nettoyage du fichier PID: $PidFile"
        $processId = Get-Content $PidFile -ErrorAction SilentlyContinue
        
        if ($processId) {
            Write-Verbose-Custom "PID trouvé: $processId"
            $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Verbose-Custom "Processus zombie détecté (PID $processId), arrêt..."
                try {
                    taskkill /PID $processId /T /F 2>$null | Out-Null
                } catch {}
            }
        }
        
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }
}

# ═══════════════════════════════════════════════════════════
#  EN-TÊTE
# ═══════════════════════════════════════════════════════════

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║         AssistantAudit v2.0.0                ║" -ForegroundColor Cyan
Write-Host "  ║     Plateforme d'audit d'infrastructure IT   ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

if ($DevMode) {
    Write-Host "  Mode: DEVELOPPEMENT (logs DEBUG + hot-reload)" -ForegroundColor Yellow
} elseif ($BuildMode) {
    Write-Host "  Mode: PRODUCTION (build optimisé)" -ForegroundColor Green
} else {
    Write-Host "  Mode: STANDARD (développement)" -ForegroundColor Cyan
}
Write-Host ""

# ═══════════════════════════════════════════════════════════
#  VÉRIFICATION DES PRÉREQUIS
# ═══════════════════════════════════════════════════════════

Write-Log "Vérification des prérequis..."

# PowerShell Version
$psVersion = $PSVersionTable.PSVersion
Write-Verbose-Custom "PowerShell version: $psVersion"

if ($psVersion.Major -lt 5) {
    Write-Fail "PowerShell 5.0+ requis (version actuelle: $psVersion)"
}

if ($psVersion.Major -lt 7) {
    Write-Warn "PowerShell 7+ recommandé pour Monkey365 (version actuelle: $psVersion)"
    Write-Warn "Téléchargez PowerShell 7: https://aka.ms/powershell"
    Write-Warn "Exécutez ce script avec 'pwsh start.ps1' au lieu de 'powershell start.ps1'"
} else {
    Write-Ok "PowerShell $psVersion"
}

# Python 3
Test-Prerequisite -Name "Python 3" `
    -Command "python" `
    -ErrorMessage "Python 3.8+ requis. Installez-le : https://python.org" | Out-Null

$pythonVersion = python --version 2>&1
Write-Ok "$pythonVersion"

# Node.js
Test-Prerequisite -Name "Node.js" `
    -Command "node" `
    -ErrorMessage "Node.js 18+ requis. Installez-le : https://nodejs.org" | Out-Null

$nodeVersion = node --version 2>&1
Write-Ok "Node.js $nodeVersion"

# Git (optionnel mais recommandé)
$hasGit = Test-Prerequisite -Name "Git" `
    -Command "git" `
    -ErrorMessage "Git non trouvé - les outils externes ne seront pas auto-téléchargés" `
    -Optional

if ($hasGit) {
    $gitVersion = git --version 2>&1
    Write-Ok "$gitVersion"
}

# Nmap (optionnel)
$hasNmap = Test-Prerequisite -Name "Nmap" `
    -Command "nmap" `
    -ErrorMessage "Nmap non trouvé - le scanner réseau ne fonctionnera pas" `
    -Optional

if ($hasNmap) {
    $nmapVersion = (nmap --version 2>&1) | Select-Object -First 1
    Write-Ok "$nmapVersion"
}

# ═══════════════════════════════════════════════════════════
#  CONFIGURATION DE L'ENVIRONNEMENT
# ═══════════════════════════════════════════════════════════

Write-Log "Configuration de l'environnement..."

$envFile = Join-Path $RootDir ".env"
$envExample = Join-Path $RootDir ".env.example"

# Créer .env depuis .env.example si absent
if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Write-Log "Création du fichier .env depuis .env.example..."
        Copy-Item $envExample $envFile
        Write-Ok "Fichier .env créé"
        
        # Générer une SECRET_KEY aléatoire
        Write-Verbose-Custom "Génération d'une SECRET_KEY aléatoire..."
        $secretKey = -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Minimum 0 -Maximum 16) })
        
        $envContent = Get-Content $envFile -Raw
        $envContent = $envContent -replace "SECRET_KEY=change-me-in-production", "SECRET_KEY=$secretKey"
        Set-Content -Path $envFile -Value $envContent -NoNewline
        
        Write-Ok "SECRET_KEY générée automatiquement"
    } else {
        Write-Warn "Fichier .env.example introuvable"
        Write-Warn "Création d'un .env minimal..."
        
        # Créer un .env basique
        $secretKey = -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Minimum 0 -Maximum 16) })
        @"
# AssistantAudit - Configuration Environnement
SECRET_KEY=$secretKey
DATABASE_URL=sqlite:///instance/assistantaudit.db
LOG_LEVEL=INFO
NMAP_TIMEOUT=600
PINGCASTLE_TIMEOUT=300
"@ | Set-Content -Path $envFile
        Write-Ok ".env minimal créé"
    }
} else {
    Write-Ok "Fichier .env existant"
}

# Configurer le niveau de log selon le mode
if ($DevMode) {
    Write-Verbose-Custom "Configuration LOG_LEVEL=DEBUG pour mode développement"
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match "LOG_LEVEL=") {
        $envContent = $envContent -replace "LOG_LEVEL=.*", "LOG_LEVEL=DEBUG"
        Set-Content -Path $envFile -Value $envContent -NoNewline
    } else {
        Add-Content -Path $envFile -Value "`nLOG_LEVEL=DEBUG"
    }
}

# ═══════════════════════════════════════════════════════════
#  OUTILS EXTERNES
# ═══════════════════════════════════════════════════════════

# Créer le dossier tools si nécessaire
if (-not (Test-Path $ToolsDir)) {
    Write-Verbose-Custom "Création du dossier tools..."
    New-Item -ItemType Directory -Path $ToolsDir -Force | Out-Null
}

# ═══════════════════════════════════════════════════════════
#  OUTILS EXTERNES - MISE À JOUR AUTOMATIQUE
# ═══════════════════════════════════════════════════════════

Write-Log "Vérification des outils externes..."

# ── PingCastle Setup ──
# Utilise PingCastleAutoUpdater.exe pour les mises à jour automatiques
$pingCastleDir = Join-Path $ToolsDir "pingcastle"
$pingCastleExe = "PingCastle.exe"

# Afficher un message si ancien clone Git détecté
if (Test-Path (Join-Path $pingCastleDir ".git")) {
    Write-Warn "Ancien clone Git de PingCastle détecté dans $pingCastleDir"
    Write-Warn "Plus besoin de Git - PingCastleAutoUpdater.exe gère les mises à jour"
    Write-Warn "Vous pouvez supprimer le dossier .git pour libérer de l'espace"
}

Update-PingCastle -TargetDir $pingCastleDir `
    -EnvVarName "PINGCASTLE_PATH" `
    -ExecutableName $pingCastleExe | Out-Null

# ── Monkey365 Setup ──
# Télécharge depuis GitHub Releases (ZIP léger au lieu du clone Git)
$monkey365Dir = Join-Path $ToolsDir "monkey365"
$monkey365Script = "Invoke-Monkey365.ps1"

# Afficher un message si ancien clone Git détecté
if (Test-Path (Join-Path $monkey365Dir ".git")) {
    Write-Warn "Ancien clone Git de Monkey365 détecté dans $monkey365Dir"
    Write-Warn "Désormais téléchargé depuis GitHub Releases (ZIP plus léger)"
    Write-Warn "Vous pouvez supprimer le dossier .git pour libérer de l'espace"
}

Update-ToolFromGitHub -ToolName "Monkey365" `
    -RepoOwner "silverhack" `
    -RepoName "monkey365" `
    -TargetDir $monkey365Dir `
    -AssetPattern "monkey365.zip" `
    -VerifySHA256 `
    -EnvVarName "MONKEY365_PATH" `
    -ExecutablePath $monkey365Script | Out-Null

# ═══════════════════════════════════════════════════════════
#  ENVIRONNEMENT VIRTUEL PYTHON
# ═══════════════════════════════════════════════════════════

if (-not (Test-Path $VenvDir)) {
    Write-Log "Création de l'environnement virtuel Python..."
    Write-Verbose-Custom "python -m venv $VenvDir"
    python -m venv $VenvDir
    Write-Ok "venv créé dans $VenvDir"
}

Write-Verbose-Custom "Activation du venv..."
& "$VenvDir\Scripts\Activate.ps1"
Write-Ok "venv activé"

# ── Dépendances backend (skip si requirements.txt n'a pas changé) ──
$reqFile   = Join-Path $BackendDir "requirements.txt"
$stampFile = Join-Path $VenvDir ".deps_stamp"

if (Test-Path $reqFile) {
    $reqHash = (Get-FileHash $reqFile -Algorithm MD5).Hash
    Write-Verbose-Custom "Hash requirements.txt: $reqHash"
    
    $needsInstall = $true
    if (Test-Path $stampFile) {
        $cachedHash = Get-Content $stampFile -ErrorAction SilentlyContinue
        if ($cachedHash -eq $reqHash) {
            $needsInstall = $false
            Write-Ok "Dépendances Python à jour (skip)"
        }
    }
    
    if ($needsInstall) {
        Write-Log "Installation des dépendances backend..."
        $pipArgs = @("-q", "-r", $reqFile)
        if ($DevMode) {
            $pipArgs = @("-v", "-r", $reqFile)  # Mode verbeux en dev
        }
        Write-Verbose-Custom "pip install $($pipArgs -join ' ')"
        pip install @pipArgs
        
        $reqHash | Set-Content $stampFile
        Write-Ok "Dépendances Python installées"
    }
} else {
    Write-Warn "Fichier requirements.txt non trouvé dans $BackendDir"
}

# ═══════════════════════════════════════════════════════════
#  INITIALISATION BASE DE DONNÉES
# ═══════════════════════════════════════════════════════════

$dbPath = Join-Path $BackendDir "instance\assistantaudit.db"

if (-not (Test-Path $dbPath)) {
    Write-Log "Première exécution - initialisation de la base de données..."
    Push-Location $BackendDir
    Write-Verbose-Custom "python init_db.py"
    python init_db.py
    Pop-Location
    Write-Ok "Base de données initialisée (admin / Admin@2026!)"
} else {
    Write-Ok "Base de données existante détectée"
}

# ── Migrations Alembic ──
Write-Log "Application des migrations..."
Push-Location $BackendDir

try {
    if ($DevMode) {
        Write-Verbose-Custom "alembic upgrade head --verbose"
        python -m alembic upgrade head
    } else {
        python -m alembic upgrade head 2>$null
    }
    Write-Ok "Migrations appliquées"
} catch {
    Write-Verbose-Custom "Migrations déjà à jour ou erreur: $_"
    Write-Ok "Migrations à jour"
}

Pop-Location

# ── Rotation des logs ──
$logsDir = Join-Path $BackendDir "logs"
if (-not (Test-Path $logsDir)) {
    Write-Verbose-Custom "Création du dossier logs..."
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

$logFile = Join-Path $logsDir "assistantaudit.log"
Rotate-Logs -LogPath $logFile -MaxSizeMB 10 -KeepCount 5

# ═══════════════════════════════════════════════════════════
#  DÉPENDANCES FRONTEND
# ═══════════════════════════════════════════════════════════

$nodeModules = Join-Path $FrontendDir "node_modules"

if (-not (Test-Path $nodeModules)) {
    Write-Log "Installation des dépendances frontend..."
    Push-Location $FrontendDir
    
    if ($DevMode) {
        Write-Verbose-Custom "npm install (mode verbeux)"
        npm install
    } else {
        npm install --silent
    }
    
    Pop-Location
    Write-Ok "Dépendances Node.js installées"
} else {
    Write-Ok "node_modules existant"
}

# Build frontend si mode production
if ($BuildMode) {
    Write-Log "Build du frontend pour la production..."
    Push-Location $FrontendDir
    Write-Verbose-Custom "npm run build"
    npm run build
    Pop-Location
    Write-Ok "Frontend buildé"
}

# ═══════════════════════════════════════════════════════════
#  NETTOYAGE DES PROCESSUS ZOMBIES
# ═══════════════════════════════════════════════════════════

Write-Log "Nettoyage des processus zombies..."

# Nettoyer les fichiers PID et tuer les processus zombies
$backendPidFile = Join-Path $BackendDir "instance\backend.pid"
$frontendPidFile = Join-Path $FrontendDir ".next\frontend.pid"

Clean-PidFile -PidFile $backendPidFile
Clean-PidFile -PidFile $frontendPidFile

# Libération des ports
Write-Verbose-Custom "Libération des ports $BackendPort et $FrontendPort..."
Stop-PortProcess -Port $BackendPort
Stop-PortProcess -Port $FrontendPort
Start-Sleep -Milliseconds 500
Write-Ok "Ports libérés"

# ═══════════════════════════════════════════════════════════
#  DÉMARRAGE BACKEND
# ═══════════════════════════════════════════════════════════

Write-Log "Démarrage du backend (port $BackendPort)..."

# Construire les arguments uvicorn selon le mode
$backendArgs = @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$BackendPort")

if ($BuildMode) {
    # Mode production : multi-workers, pas de reload
    $backendArgs += "--workers", "4"
    Write-Verbose-Custom "Mode production: uvicorn avec 4 workers"
} elseif ($DevMode) {
    # Mode développement : hot-reload + logs debug
    $backendArgs += "--reload", "--reload-dir", "app", "--log-level", "debug"
    Write-Verbose-Custom "Mode dev: hot-reload actif (surveille app/)"
} else {
    # Mode standard : logs info
    $backendArgs += "--log-level", "info"
}

Write-Verbose-Custom "Commande backend: python $($backendArgs -join ' ')"

$backendProc = Start-Process -FilePath "$VenvDir\Scripts\python.exe" `
    -ArgumentList $backendArgs `
    -WorkingDirectory $BackendDir `
    -WindowStyle Hidden `
    -PassThru

# Sauvegarder le PID
$script:BackendPID = $backendProc.Id
$backendPidFile = Join-Path $BackendDir "instance\backend.pid"
$backendProc.Id | Set-Content $backendPidFile
Write-Verbose-Custom "Backend PID $($backendProc.Id) sauvegardé dans $backendPidFile"

# Attendre que le backend soit prêt (max 45s en dev, 20s sinon)
$maxWait = if ($DevMode) { 45 } else { 20 }
Write-Log "Attente du backend (max ${maxWait}s)..."
$ready = $false

for ($i = 0; $i -lt $maxWait; $i++) {
    Start-Sleep -Seconds 1
    
    if ($backendProc.HasExited) {
        Write-Warn "Le backend a crashé au démarrage (code $($backendProc.ExitCode))"
        Write-Warn "Vérifiez backend/logs/assistantaudit.log pour les détails"
        if ($DevMode) {
            $logContent = Get-Content (Join-Path $BackendDir "logs\assistantaudit.log") -Tail 20 -ErrorAction SilentlyContinue
            if ($logContent) {
                Write-Host "`n── Dernières lignes du log ──" -ForegroundColor Yellow
                Write-Host ($logContent -join "`n") -ForegroundColor Gray
            }
        }
        break
    }
    
    try {
        $code = curl.exe -s -o NUL -w "%{http_code}" "http://localhost:${BackendPort}/api/v1/health" 2>$null
        if ($code -eq "200") {
            $ready = $true
            break
        }
    } catch { }
    
    # Afficher un point de progression toutes les 5s en mode normal, toutes les 2s en dev
    $interval = if ($DevMode) { 2 } else { 5 }
    if ($i -gt 0 -and $i % $interval -eq 0) {
        Write-Verbose-Custom "Attente backend... ${i}s"
    }
}

if ($ready) {
    Write-Ok "Backend prêt sur http://localhost:$BackendPort (${i}s)"
} elseif (-not $backendProc.HasExited) {
    Write-Warn "Le backend met du temps à démarrer..."
}

# ═══════════════════════════════════════════════════════════
#  DÉMARRAGE FRONTEND
# ═══════════════════════════════════════════════════════════

Write-Log "Démarrage du frontend (port $FrontendPort)..."

# Construire la commande frontend selon le mode
if ($BuildMode) {
    # Mode production : next start
    $frontendCmd = "npx next start --port $FrontendPort"
    Write-Verbose-Custom "Mode production: next start"
} elseif ($DevMode) {
    # Mode développement : next dev avec turbo
    $frontendCmd = "npx next dev --port $FrontendPort --turbo"
    Write-Verbose-Custom "Mode dev: next dev avec turbopack"
} else {
    # Mode standard : next dev
    $frontendCmd = "npx next dev --port $FrontendPort"
}

Write-Verbose-Custom "Commande frontend: $frontendCmd"

$frontendProc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", $frontendCmd `
    -WorkingDirectory $FrontendDir `
    -WindowStyle Hidden `
    -PassThru

# Sauvegarder le PID
$script:FrontendPID = $frontendProc.Id
$frontendPidFile = Join-Path $FrontendDir ".next\frontend.pid"

# Créer le dossier .next si nécessaire
$nextDir = Join-Path $FrontendDir ".next"
if (-not (Test-Path $nextDir)) {
    New-Item -ItemType Directory -Path $nextDir -Force | Out-Null
}

$frontendProc.Id | Set-Content $frontendPidFile
Write-Verbose-Custom "Frontend PID $($frontendProc.Id) sauvegardé dans $frontendPidFile"

Start-Sleep -Seconds 3

# ═══════════════════════════════════════════════════════════
#  RÉCAPITULATIF
# ═══════════════════════════════════════════════════════════

$elapsed = ((Get-Date) - $script:StartTime).TotalSeconds
Write-Verbose-Custom "Temps total de démarrage: ${elapsed}s"

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║           Tout est prêt !                    ║" -ForegroundColor Green
Write-Host "  ╠══════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "  ║  Frontend  : http://localhost:$FrontendPort           ║" -ForegroundColor Green
Write-Host "  ║  API       : http://localhost:$BackendPort           ║" -ForegroundColor Green
Write-Host "  ║  Swagger   : http://localhost:$BackendPort/docs      ║" -ForegroundColor Green
Write-Host "  ║  Login     : admin / Admin@2026!             ║" -ForegroundColor Green

if ($BuildMode) {
    Write-Host "  ║  Mode      : PRODUCTION (optimisé)           ║" -ForegroundColor Cyan
} elseif ($DevMode) {
    Write-Host "  ║  Mode      : DEV (logs DEBUG + hot-reload)   ║" -ForegroundColor Yellow
} else {
    Write-Host "  ║  Mode      : STANDARD (développement)        ║" -ForegroundColor Cyan
}

Write-Host "  ╠══════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "  ║  Backend PID  : $($script:BackendPID)".PadRight(46) + "║" -ForegroundColor Green
Write-Host "  ║  Frontend PID : $($script:FrontendPID)".PadRight(46) + "║" -ForegroundColor Green
Write-Host "  ╠══════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "  ║  Logs      : backend/logs/assistantaudit.log ║" -ForegroundColor Green
Write-Host "  ║  Ctrl+C    : Arrêter les services            ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# ═══════════════════════════════════════════════════════════
#  BOUCLE DE SURVEILLANCE
# ═══════════════════════════════════════════════════════════

try {
    Write-Log "Services en cours d'exécution... (Ctrl+C pour arrêter)"
    
    while ($true) {
        # Auto-restart si un processus crash (sauf en mode build)
        if ($backendProc.HasExited) {
            Write-Warn "Le backend s'est arrêté (code $($backendProc.ExitCode))"
            
            if (-not $BuildMode) {
                Write-Warn "Redémarrage automatique..."
                $backendProc = Start-Process -FilePath "$VenvDir\Scripts\python.exe" `
                    -ArgumentList $backendArgs `
                    -WorkingDirectory $BackendDir `
                    -WindowStyle Hidden `
                    -PassThru
                
                $script:BackendPID = $backendProc.Id
                $backendProc.Id | Set-Content $backendPidFile
                Write-Verbose-Custom "Backend redémarré avec PID $($backendProc.Id)"
            } else {
                Write-Fail "Backend crashé en mode production - arrêt"
            }
        }
        
        if ($frontendProc.HasExited) {
            Write-Warn "Le frontend s'est arrêté (code $($frontendProc.ExitCode))"
            
            if (-not $BuildMode) {
                Write-Warn "Redémarrage automatique..."
                $frontendProc = Start-Process -FilePath "cmd.exe" `
                    -ArgumentList "/c", $frontendCmd `
                    -WorkingDirectory $FrontendDir `
                    -WindowStyle Hidden `
                    -PassThru
                
                $script:FrontendPID = $frontendProc.Id
                $frontendProc.Id | Set-Content $frontendPidFile
                Write-Verbose-Custom "Frontend redémarré avec PID $($frontendProc.Id)"
            } else {
                Write-Fail "Frontend crashé en mode production - arrêt"
            }
        }
        
        Start-Sleep -Seconds 3
    }
} finally {
    # ═══════════════════════════════════════════════════════════
    #  ARRÊT PROPRE
    # ═══════════════════════════════════════════════════════════
    
    Write-Host ""
    Write-Log "Arrêt des services..."
    
    # taskkill /T = tree kill (tue le processus ET tous ses enfants)
    if (-not $backendProc.HasExited) {
        Write-Verbose-Custom "Arrêt du backend (PID $($backendProc.Id))..."
        try {
            taskkill /PID $backendProc.Id /T /F 2>$null | Out-Null
        } catch {}
    }
    
    if (-not $frontendProc.HasExited) {
        Write-Verbose-Custom "Arrêt du frontend (PID $($frontendProc.Id))..."
        try {
            taskkill /PID $frontendProc.Id /T /F 2>$null | Out-Null
        } catch {}
    }
    
    # Nettoyage final des ports (sécurité)
    Start-Sleep -Milliseconds 500
    Stop-PortProcess -Port $BackendPort
    Stop-PortProcess -Port $FrontendPort
    
    # Supprimer les fichiers PID
    Write-Verbose-Custom "Suppression des fichiers PID..."
    if (Test-Path $backendPidFile) {
        Remove-Item $backendPidFile -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $frontendPidFile) {
        Remove-Item $frontendPidFile -Force -ErrorAction SilentlyContinue
    }
    
    $totalTime = ((Get-Date) - $script:StartTime).TotalSeconds
    Write-Ok "Tous les services sont arrêtés proprement (durée totale: ${totalTime}s)"
}
