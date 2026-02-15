<#
.SYNOPSIS
    Test des nouvelles fonctions de mise à jour des outils
#>

$ErrorActionPreference = "Stop"

# Importer les fonctions du script principal
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ToolsDir = Join-Path $RootDir "tools"

Write-Host "=== Test des fonctions de mise à jour des outils ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Vérifier l'API GitHub pour Monkey365
Write-Host "[1] Test de l'API GitHub Releases (Monkey365)..." -ForegroundColor Yellow
try {
    $apiUrl = "https://api.github.com/repos/silverhack/monkey365/releases/latest"
    $release = Invoke-RestMethod -Uri $apiUrl -Headers @{
        'User-Agent' = 'AssistantAudit-PowerShell'
        'Accept' = 'application/vnd.github.v3+json'
    }
    
    Write-Host "  ✓ Dernière version: $($release.tag_name)" -ForegroundColor Green
    Write-Host "  ✓ Publiée le: $($release.published_at)" -ForegroundColor Green
    
    $zipAsset = $release.assets | Where-Object { $_.name -like "monkey365.zip" } | Select-Object -First 1
    if ($zipAsset) {
        Write-Host "  ✓ Asset ZIP trouvé: $($zipAsset.name) ($([math]::Round($zipAsset.size / 1MB, 2)) MB)" -ForegroundColor Green
        Write-Host "  ✓ URL: $($zipAsset.browser_download_url)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Asset ZIP non trouvé" -ForegroundColor Red
    }
    
    $sha256Asset = $release.assets | Where-Object { $_.name -like "*.sha256" } | Select-Object -First 1
    if ($sha256Asset) {
        Write-Host "  ✓ Fichier SHA256 disponible: $($sha256Asset.name)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Fichier SHA256 non disponible" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "  ✗ Erreur: $_" -ForegroundColor Red
}

Write-Host ""

# Test 2: Vérifier PingCastle AutoUpdater
Write-Host "[2] Test de PingCastle AutoUpdater..." -ForegroundColor Yellow
$pingCastleDir = Join-Path $ToolsDir "pingcastle"
$autoUpdaterPath = Join-Path $pingCastleDir "PingCastleAutoUpdater.exe"
$pingCastlePath = Join-Path $pingCastleDir "PingCastle.exe"

if (Test-Path $pingCastleDir) {
    Write-Host "  ✓ Dossier PingCastle trouvé: $pingCastleDir" -ForegroundColor Green
    
    if (Test-Path $pingCastlePath) {
        Write-Host "  ✓ PingCastle.exe trouvé" -ForegroundColor Green
        
        # Obtenir la version
        $versionInfo = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($pingCastlePath)
        Write-Host "  ✓ Version: $($versionInfo.FileVersion)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ PingCastle.exe non trouvé" -ForegroundColor Red
    }
    
    if (Test-Path $autoUpdaterPath) {
        Write-Host "  ✓ PingCastleAutoUpdater.exe trouvé" -ForegroundColor Green
        
        # Tester avec --help
        try {
            $helpOutput = & $autoUpdaterPath --help 2>&1
            if ($LASTEXITCODE -eq 0 -or $helpOutput) {
                Write-Host "  ✓ AutoUpdater fonctionnel (--help OK)" -ForegroundColor Green
            }
        } catch {
            Write-Host "  ⚠ AutoUpdater présent mais erreur lors du test: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ✗ PingCastleAutoUpdater.exe non trouvé" -ForegroundColor Red
        Write-Host "    → Téléchargez PingCastle depuis https://github.com/netwrix/pingcastle/releases/latest" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ Dossier PingCastle non trouvé: $pingCastleDir" -ForegroundColor Red
    Write-Host "    → Créez le dossier et téléchargez PingCastle" -ForegroundColor Yellow
}

Write-Host ""

# Test 3: Vérifier Monkey365
Write-Host "[3] Test de Monkey365..." -ForegroundColor Yellow
$monkey365Dir = Join-Path $ToolsDir "monkey365"
$monkey365Script = Join-Path $monkey365Dir "Invoke-Monkey365.ps1"
$versionFile = Join-Path $monkey365Dir ".version"

if (Test-Path $monkey365Dir) {
    Write-Host "  ✓ Dossier Monkey365 trouvé: $monkey365Dir" -ForegroundColor Green
    
    if (Test-Path $versionFile) {
        $currentVersion = Get-Content $versionFile -Raw | ForEach-Object { $_.Trim() }
        Write-Host "  ✓ Version locale: $currentVersion" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Fichier .version non trouvé (première installation ou ancien clone Git)" -ForegroundColor Yellow
    }
    
    if (Test-Path $monkey365Script) {
        Write-Host "  ✓ Invoke-Monkey365.ps1 trouvé" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Invoke-Monkey365.ps1 non trouvé" -ForegroundColor Red
    }
    
    # Vérifier si c'est un clone Git (ancien système)
    if (Test-Path (Join-Path $monkey365Dir ".git")) {
        Write-Host "  ⚠ Ancien clone Git détecté (.git présent)" -ForegroundColor Yellow
        Write-Host "    → Le nouveau système télécharge depuis GitHub Releases (plus léger)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠ Dossier Monkey365 non trouvé: $monkey365Dir" -ForegroundColor Yellow
    Write-Host "    → Sera créé automatiquement lors du premier lancement de start.ps1" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Test terminé ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pour appliquer les mises à jour, exécutez: .\start.ps1 --dev" -ForegroundColor Green
