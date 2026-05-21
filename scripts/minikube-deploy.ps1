param(
  [switch]$Start,
  [switch]$NoCache,
  [switch]$SkipBuild,
  [switch]$SkipApply
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($Start) {
  minikube start
}

Write-Host "Pointing Docker CLI at Minikube's Docker daemon..."
minikube docker-env --shell powershell | Invoke-Expression

if (-not $SkipBuild) {
  $buildArgs = @("build")
  if ($NoCache) { $buildArgs += "--no-cache" }

  $backendBuildArgs = $buildArgs + @("-t", "bugswarm-backend:local", ".\backend")
  $workerBuildArgs = $buildArgs + @("-t", "bugswarm-worker:local", ".\worker")
  $frontendBuildArgs = $buildArgs + @("-t", "bugswarm-frontend:local", ".\frontend")
  $buggyshopBuildArgs = $buildArgs + @("-t", "bugswarm-buggyshop:local", ".\demo\buggyshop")

  docker @backendBuildArgs
  docker @workerBuildArgs
  docker @frontendBuildArgs
  docker @buggyshopBuildArgs
}

if (-not $SkipApply) {
  kubectl apply -k .\k8s\minikube
  kubectl -n bugswarm rollout status deployment/bugswarm-backend --timeout=180s
  kubectl -n bugswarm rollout status deployment/bugswarm-worker --timeout=180s
  kubectl -n bugswarm rollout status deployment/bugswarm-frontend --timeout=180s
}

Write-Host ""
Write-Host "Port-forward commands:"
Write-Host "kubectl -n bugswarm port-forward svc/bugswarm-frontend 5173:5173"
Write-Host "kubectl -n bugswarm port-forward svc/bugswarm-backend 8000:8000"
Write-Host "kubectl -n bugswarm port-forward svc/buggyshop 8090:8090"
