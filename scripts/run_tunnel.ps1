# Run De-Influence AI behind a FREE HTTPS tunnel so it is INSTALLABLE as a PWA on a phone.
#
# Why: browsers only allow "Add to Home screen" as a real app over HTTPS (or localhost).
# A phone hitting http://<PC-IP>:8000 will NOT offer install (you only get a shortcut).
# A tunnel gives you a public https:// URL that forwards to your local server, which is
# what lets the phone install it as a standalone app.
#
# This uses the official cloudflared.exe binary (a single self-contained file, no npm, no
# account). The script downloads it to tools/cloudflared.exe the first time if it is missing.
#
# Usage:
#   1. Terminal A:  python -m uvicorn app.main:app --port 8000
#   2. Terminal B:  powershell -ExecutionPolicy Bypass -File scripts/run_tunnel.ps1
#
# Then watch terminal B for:  https://<random>.trycloudflare.com
# Open THAT url on your phone, and install from the browser menu.
# Ctrl+C in terminal B stops the tunnel.

$ErrorActionPreference = "Stop"

# Resolve paths relative to the repo root (this script lives in scripts/).
$root = Split-Path -Parent $PSScriptRoot
$exe  = Join-Path $root "tools\cloudflared.exe"

if (-not (Test-Path $exe)) {
    Write-Host "cloudflared.exe not found - downloading the official binary (~55 MB, one time)..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path (Split-Path $exe) | Out-Null
    $url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    try {
        Invoke-WebRequest -Uri $url -OutFile $exe -UseBasicParsing
    } catch {
        Write-Host "Download failed: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Download it manually from https://github.com/cloudflare/cloudflared/releases/latest" -ForegroundColor Red
        Write-Host "and save it as:  $exe" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Starting a free HTTPS tunnel to http://localhost:8000 ..." -ForegroundColor Cyan
Write-Host "Make sure the app is running in another terminal:" -ForegroundColor Cyan
Write-Host "    python -m uvicorn app.main:app --port 8000" -ForegroundColor Gray
Write-Host ""
Write-Host "Watch for a line like:  https://something-random.trycloudflare.com" -ForegroundColor Green
Write-Host "Open that URL on your phone, then browser menu -> Add to Home screen / Install app." -ForegroundColor Green
Write-Host ""

& $exe tunnel --url http://localhost:8000
