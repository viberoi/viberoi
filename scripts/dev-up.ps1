#!/usr/bin/env pwsh
# Bring up local infra: Postgres + Redis + LocalStack.
# Idempotent — safe to run repeatedly.

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "Starting VibeROI local infra..." -ForegroundColor Cyan
docker compose up -d

Write-Host "`nWaiting for services to be healthy..." -ForegroundColor Cyan
$timeout = 90
$elapsed = 0
do {
    Start-Sleep -Seconds 3
    $elapsed += 3
    $output = docker compose ps --format json 2>$null
    if (-not $output) { continue }
    # docker compose ps emits one JSON object per line
    $statuses = $output -split "`n" | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json }
    $unhealthy = $statuses | Where-Object { $_.Health -and $_.Health -ne "healthy" }
    if (-not $unhealthy) { break }
    Write-Host "  ... waiting (${elapsed}s)" -ForegroundColor DarkGray
} while ($elapsed -lt $timeout)

Write-Host "`nStatus:" -ForegroundColor Green
docker compose ps

Write-Host @"

Postgres:   localhost:5432  (user: viberoi, password: viberoi, db: viberoi)
Redis:      localhost:6379
LocalStack: localhost:4566  (S3, SQS, KMS, Secrets Manager)

Next:
  uv sync
  uv run alembic upgrade head    # once migrations exist
  uv run pytest

"@ -ForegroundColor White
