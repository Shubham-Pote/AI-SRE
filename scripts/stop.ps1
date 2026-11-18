$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose stop
if ($LASTEXITCODE -ne 0) { throw 'Could not stop the dashboard services' }
docker stop heal-lab-control-plane
if ($LASTEXITCODE -ne 0) { throw 'Could not stop the demo cluster' }
Write-Host 'HealLab stopped. Images and data are retained. Run scripts/setup.ps1 to resume.'
