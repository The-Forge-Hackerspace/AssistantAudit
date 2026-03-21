# Install Microsoft 365 PowerShell Modules
# Run this as Administrator

Write-Host "Checking if running as Administrator..." -ForegroundColor Cyan
$isAdmin = [bool]([System.Security.Principal.WindowsIdentity]::GetCurrent().Groups -match 'S-1-5-32-544')
if (-not $isAdmin) {
    Write-Host "❌ ERROR: This script must run as Administrator" -ForegroundColor Red
    Write-Host "Please right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Running as Administrator" -ForegroundColor Green
Write-Host ""

Write-Host "Setting PSGallery as trusted..." -ForegroundColor Cyan
Set-PSRepository -Name PSGallery -InstallationPolicy Trusted -ErrorAction SilentlyContinue

Write-Host "Installing Microsoft 365 PowerShell modules..." -ForegroundColor Cyan
Write-Host ""

$modules = @(
    'ExchangeOnlineManagement',
    'MicrosoftTeams',
    'PnP.PowerShell',
    'Microsoft.Graph.Authentication'
)

$installed = @()
$failed = @()

foreach ($module in $modules) {
    Write-Host "Installing $module..." -ForegroundColor Yellow
    try {
        Install-Module -Name $module -Force -AllowClobber -ErrorAction Stop
        Write-Host "  ✅ $module installed successfully" -ForegroundColor Green
        $installed += $module
    } catch {
        Write-Host "  ❌ $module installation failed: $_" -ForegroundColor Red
        $failed += $module
    }
    Write-Host ""
}

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Installation Summary" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Installed: $($installed.Count)/$($modules.Count)" -ForegroundColor Green
Write-Host ""

if ($installed) {
    Write-Host "✅ Successfully installed:" -ForegroundColor Green
    foreach ($m in $installed) {
        Write-Host "   - $m" -ForegroundColor Green
    }
}

if ($failed) {
    Write-Host ""
    Write-Host "⚠️  Failed to install:" -ForegroundColor Red
    foreach ($m in $failed) {
        Write-Host "   - $m" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Try running individually:" -ForegroundColor Yellow
    foreach ($m in $failed) {
        Write-Host "  Install-Module -Name $m -Force" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Verifying all modules are available..." -ForegroundColor Cyan
$allAvailable = $true
foreach ($module in $modules) {
    if (Get-Module -Name $module -ListAvailable -ErrorAction SilentlyContinue) {
        Write-Host "  ✅ $module" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $module NOT available" -ForegroundColor Red
        $allAvailable = $false
    }
}

Write-Host ""
if ($allAvailable) {
    Write-Host "✅ All modules installed and ready!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some modules are still missing. Try running as Administrator again." -ForegroundColor Yellow
}
