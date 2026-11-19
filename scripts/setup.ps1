$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Check { if ($LASTEXITCODE -ne 0) { throw "Previous command failed: $LASTEXITCODE" } }
function CheckSpace {
    $available = (Get-PSDrive C).Free
    if ($null -ne $available -and $available -lt 10GB) { throw 'Less than 10 GB remains on C:. Stop setup and free space before continuing.' }
}
CheckSpace
docker info --format '{{.ServerVersion}}'; Check
if (-not (Test-Path '.tools/kind.exe')) {
    New-Item -ItemType Directory -Force .tools | Out-Null
    Invoke-WebRequest https://kind.sigs.k8s.io/dl/v0.27.0/kind-windows-amd64 -OutFile .tools/kind.exe
}
$clusters = & ./.tools/kind.exe get clusters
Check
if ($clusters -notcontains 'heal-lab') {
    & ./.tools/kind.exe create cluster --name heal-lab --config infra/kind.yaml; Check
} else {
    docker start heal-lab-control-plane; Check
    kubectl --context kind-heal-lab wait --for=condition=Ready node/heal-lab-control-plane --timeout=120s; Check
}
docker build -t heallab-demo:local .; Check
CheckSpace
& ./.tools/kind.exe load docker-image heallab-demo:local --name heal-lab; Check
kubectl --context kind-heal-lab apply -f infra/demo.yaml -f infra/monitoring.yaml -f infra/load.yaml; Check
kubectl --context kind-heal-lab -n heal-demo rollout status deployment/demo --timeout=180s; Check
# Internal endpoint is reachable by containers on the kind Docker network.
& ./.tools/kind.exe get kubeconfig --name heal-lab --internal | Set-Content data/admin-kubeconfig -Encoding utf8
$cfg = kubectl --kubeconfig data/admin-kubeconfig config view --raw -o json | ConvertFrom-Json
Check
$token = kubectl --context kind-heal-lab -n heal-demo create token controller --duration=24h
Check
$cfg.users = @(@{name='controller';user=@{token=$token}})
$cfg.contexts[0].context.user = 'controller'
$cfg | ConvertTo-Json -Depth 20 | Set-Content data/kubeconfig -Encoding utf8
Remove-Item -LiteralPath data/admin-kubeconfig
# Controller credentials expire; rerun setup to renew them.
docker build -f Dockerfile.control -t heallab-control:local .; Check
CheckSpace
docker compose up -d; Check
# Existing clients cache service-account credentials; reload the renewed token.
docker compose restart api worker; Check
Write-Host 'Console: http://localhost:8501 | Grafana: http://localhost:3000'
