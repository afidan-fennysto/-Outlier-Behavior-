# Run De-Influence AI so a phone on the same Wi-Fi can reach it.
#
# This binds to 0.0.0.0 (all network interfaces) instead of 127.0.0.1, so the server is
# reachable at http://<your-PC-IP>:8000 from other devices on the LAN.
#
# NOTE: this gives you LAN access (the page loads on your phone), but PWA "install" needs
# HTTPS. For a truly installable app, use an HTTPS tunnel instead - see scripts/run_tunnel.ps1.
#
# Usage:   powershell -ExecutionPolicy Bypass -File scripts/run_mobile.ps1

$ip = (Get-NetIPAddress -AddressFamily IPv4 |
       Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.*' } |
       Select-Object -First 1 -ExpandProperty IPAddress)

Write-Host ""
Write-Host "De-Influence AI is starting on your local network." -ForegroundColor Cyan
Write-Host "On your phone (same Wi-Fi), open:  http://$ip:8000" -ForegroundColor Green
Write-Host "(Install-to-home-screen needs HTTPS - use run_tunnel.ps1 for that.)" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
