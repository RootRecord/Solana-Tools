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

$DistRoot = Join-Path $RepoRoot "dist\Solana Tools"
$DistEnv = Join-Path $RepoRoot "dist\Solana Tools\.env.example"
if (!(Test-Path $DistEnv)) {
    Copy-Item ".env.example" $DistEnv
}

Copy-Item "package.json" (Join-Path $DistRoot "package.json") -Force
Copy-Item "tsconfig.json" (Join-Path $DistRoot "tsconfig.json") -Force
Copy-Item "ts_actions" (Join-Path $DistRoot "ts_actions") -Recurse -Force

Write-Host ""
Write-Host "Build complete:" -ForegroundColor Green
Write-Host "  dist\Solana Tools\Solana Tools.exe"
Write-Host ""
Write-Host "Copy .env.example to .env next to the exe and fill in local values before running transaction actions."
Write-Host "Use the dashboard's Install/Repair Dependencies button to install Node SDK packages for TypeScript actions."
