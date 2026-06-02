#!/usr/bin/env pwsh
# Stop the local infra. Volumes persist by default.
# To wipe all data: docker compose down -v

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "Stopping VibeROI local infra..." -ForegroundColor Cyan
docker compose down
Write-Host "Done. Volumes preserved. Wipe with: docker compose down -v" -ForegroundColor Yellow
