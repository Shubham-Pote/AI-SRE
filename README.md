# HealLab

Local infrastructure monitoring, diagnosis and verified recovery for a final-year project.

## Start on Windows

Requires Docker Desktop running Linux containers, kubectl, PowerShell and internet access. Python runs in pinned Python 3.12 containers; the host Python 3.14 installation is not used. The setup script downloads kind into `.tools` and creates only the `heal-lab` cluster.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

Open **http://localhost:8501** for Streamlit, **http://localhost:3000/d/heallab** for Grafana, and **http://localhost:8000/docs** for the API. All published ports bind to localhost. The API is a local demonstration API, without multi-user authentication.

The worker uses a namespace-scoped service-account token, valid for 24 hours. Rerun setup to renew it. Do not commit `data/`. Grafana is viewer-only and provisioned from files.

## Demo

Setup starts lightweight background traffic at five requests/second. For a measured load run, stop background traffic with `kubectl --context kind-heal-lab -n heal-demo scale deployment/traffic --replicas=0`, then run:

```powershell
docker compose run --rm worker python scripts/load.py --url http://heal-lab-control-plane:30080 --seconds 900 --rps 5
```

Wait until telemetry is healthy for at least three observations. Choose **automatic** in Streamlit and apply it. Inject a faulty revision:

```powershell
docker compose run --rm worker python scripts/experiment.py errors
```

Watch the diagnosis, rollback, and three-window verification in the incident timeline. Restore the baseline between experiments:

```powershell
docker compose run --rm worker python scripts/experiment.py none
```

Other scenarios: `memory` grows memory gradually; `cpu` adds CPU-bound work (increase load to observe saturation). Memory replacement is a temporary mitigation: the injected leak remains in the deployment. A recurring fault may escalate, and scale-out does not guarantee recovery. The controller never claims recovery without healthy traffic. Keep the five-minute cooldown between independent trials.

## ML

The system uses diagnostic rules and optional Isolation Forest evidence. No accuracy claims are bundled. Collect separate healthy traffic runs:

```powershell
docker compose run --rm worker python scripts/collect.py --output data/train.jsonl --windows 60
docker compose run --rm worker python scripts/collect.py --output data/validation.jsonl --windows 20
docker compose run --rm worker python scripts/train.py --train data/train.jsonl --validation data/validation.jsonl
```

Isolation Forest scores are displayed and attached to incidents. Three consecutive anomalies without a supported diagnosis create a manual-review incident; they do not independently authorize recovery. Memory forecasting uses a stable linear trend with R-squared >= 0.8. This is a narrow memory-limit warning, not general failure prediction.

For an exploratory baseline after at least 15 minutes of healthy traffic, run `docker compose run --rm worker python scripts/bootstrap_model.py`. It uses actual Prometheus history, selects healthy windows, and separates the holdout by more than one minute. It saves dataset provenance. This does not replace experiments across independent normal and faulty workloads.

## Evaluation and tests

```powershell
docker compose run --rm api pytest -q
docker compose run --rm api python scripts/report.py data/load.jsonl
docker compose run --rm api python scripts/smoke.py
docker compose run --rm api python scripts/summarize_recovery.py
```

Compare observe-only Kubernetes behavior with automatic rule-based recovery and trained-model observations under the same load seed. Perform five trials per scenario, preserving load files with distinct `--output` values. ML currently supplies evidence rather than a different actuation policy; do not claim ML improves recovery time without implementing and testing a distinct policy. Detection timestamps and action outcomes are available through `/incidents` and SQLite. A full academic benchmark, trained model, HPA comparison, and cloud validation remain experiment work.

## Operations

- `docker compose logs worker` diagnoses observation or Kubernetes connection errors.
- Stop new actions through the console; observation and verification continue.
- `docker compose down` stops the control plane and dashboards, retaining incident data.
- `powershell -ExecutionPolicy Bypass -File scripts/stop.ps1` stops both the dashboards and the Kubernetes container to release RAM, without deleting images or data. Run `scripts/setup.ps1` again to resume.
- `.tools/kind.exe delete cluster --name heal-lab` removes only the disposable test cluster when you choose to clean up.
- Prometheus data is ephemeral; export evaluation data before replacing its pod.
- A single worker is supported. Do not scale worker replicas against SQLite.
- API, worker and console share a single image. Setup checks for 10 GB free on C: between stages. Container logs are limited to two 10 MB files per service; Prometheus retention is six hours / 256 MB.
- Rebuild code changes with `docker build -f Dockerfile.control -t heallab-control:local .`, then run `docker compose up -d`.
- Keep a single small cluster on an 8 GB host. This is multi-cluster-ready architecture, not a validated multi-cloud system.

## Implementation layout

`controller/`: telemetry adapter, pure policies, persistent state, worker, API and ML inference.
`demo/`: instrumented fault-injectable application.
`console/`: Streamlit monitoring interface.
`infra/`: Kubernetes manifests and provisioned Grafana dashboards.
`scripts/`: setup, load, fault injection, dataset collection, training and summary commands.

Recovery actions are allowlisted, capped at three replicas, and limited to one attempt per incident (stricter than the planned two-attempt ceiling). Unknown failures escalate. Restarted workers verify pending actions without replaying them. Live integration results should be recorded separately from unit-test results.
