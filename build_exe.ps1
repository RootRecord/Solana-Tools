$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "Building Solana Tools.exe..." -ForegroundColor Cyan

if (Test-Path ".env") {
    Write-Host "Found local .env. It will NOT be bundled." -ForegroundColor Yellow
}

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller .\SolanaTools.spec --noconfirm --clean

$DistEnv = Join-Path $RepoRoot "dist\Solana Tools\.env.example"
if (!(Test-Path $DistEnv)) {
    Copy-Item ".env.example" $DistEnv
}

Write-Host ""
Write-Host "Build complete:" -ForegroundColor Green
Write-Host "  dist\Solana Tools\Solana Tools.exe"
Write-Host ""
Write-Host "Copy .env.example to .env next to the exe and fill in local values before running transaction actions."
