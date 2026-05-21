param(
  [switch]$ResetVolumes,
  [switch]$NoCache,
  [switch]$Pull,
  [switch]$SkipStart
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example"
}

New-Item -ItemType Directory -Force "storage\screenshots", "storage\traces", "storage\reports" | Out-Null

Write-Host "Stopping any existing BugSwarm compose resources..."
docker compose down --remove-orphans

if ($ResetVolumes) {
  Write-Host "Resetting compose volumes for a clean database..."
  docker compose down --volumes --remove-orphans
}

$buildArgs = @("compose", "build")
if ($Pull) { $buildArgs += "--pull" }
if ($NoCache) { $buildArgs += "--no-cache" }

Write-Host "Building BugSwarm images..."
docker @buildArgs

if (-not $SkipStart) {
  Write-Host "Starting BugSwarm..."
  docker compose up -d
  docker compose ps
  Write-Host ""
  Write-Host "Frontend:   http://localhost:5173"
  Write-Host "Backend:    http://localhost:8000/api/health"
  Write-Host "BuggyShop:  http://localhost:8090"
}
