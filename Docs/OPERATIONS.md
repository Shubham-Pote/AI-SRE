# Operating the local prototype

Run commands from the repository root in PowerShell unless a step says otherwise. These procedures act on the disposable `kind-heal-lab` cluster, `heal-demo` namespace, and `demo` Deployment. Fault injection and automatic recovery mutate that workload.

## Prerequisites and first start

- Windows PowerShell, Docker Desktop with its Linux engine running, `kubectl`, internet access for images and the initial kind download, and enough disk space. Setup stops if less than 10 GB is free on C:.
- Python runs inside pinned Python 3.12 images; host Python is not required for the normal workflow.
- Keep one small cluster on an 8 GB host. The first build and image download can take time.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

The script checks Docker, downloads kind v0.27.0 into ignored `.tools/` if needed, creates or resumes `heal-lab`, builds and loads the demo image, applies the Kubernetes manifests, creates a 24-hour namespace-scoped controller token, builds the shared control image, and starts Compose services. Rerun setup when the token expires or after stopping the cluster. Setup is designed to resume; it does not erase `data/` or the cluster.

| Interface | Local address | Use |
| --- | --- | --- |
| Streamlit console | `http://localhost:8501` | Modes, fault controls, live cards, incidents |
| Grafana dashboard | `http://localhost:3000/d/heallab` | Prometheus graphs, viewer access |
| FastAPI docs | `http://localhost:8000/docs` | Endpoint inspection and local API calls |

Wait for the console to show fresh telemetry, two ready replicas, normal requests, and **Rollback baseline available**. Baseline promotion needs sustained healthy traffic and a complete rollout; do not inject the first error fault before it appears.

## Five-minute demonstration

This presentation shows healthy traffic, a bad revision, rule-based detection, bounded rollback, and verified recovery. The optional ML model supplies evidence; it is not the decision maker for rollback.

1. Before presenting, start Docker Desktop and run `scripts/setup.ps1`. Open Streamlit and Grafana. Wait for fresh telemetry, two ready replicas, zero errors, and **Rollback baseline available**. Keep background demo traffic running.
2. Explain that Kubernetes probes and Prometheus monitor the two application replicas, while `/work` supplies user-visible request evidence.
3. Select **automatic** and click **Apply mode**. Confirm the overview says **Mode: AUTOMATIC**; changing the dropdown alone does not apply it.
4. Select **errors** and click **Apply experiment** once. This creates a faulty revision whose `/work` requests fail even though its health and readiness probes still pass.
5. Watch the error percentage and open the newest incident. Show its evidence, policy event, rollback action, and **VERIFYING** state. Do not restore the application manually during verification.
6. Wait for **RESOLVED**, zero errors, and two healthy replicas. Three healthy observations are required; allow several minutes. If the incident escalates, present that result honestly and inspect its policy/events.
7. Click **Stop new recovery actions**. Select `none` and apply it if a manual reset is needed. Allow the five-minute cooldown before another automated trial.

If the live environment fails, use only clearly labeled saved rehearsal evidence or screenshots, if available. Keep failed trials and incidents in the record. The `cpu` and `memory` paths are separate experiments and should not be presented as proven by this rollback demonstration. Stop the system afterward with `scripts/stop.ps1` if you need to release RAM.

## Daily operating sequence

1. Start or resume with `scripts/setup.ps1`.
2. Open the Streamlit console. Its recovery mode selection is **not applied** until you click **Apply mode**.
3. Keep **observe** mode when inspecting an unfamiliar condition. Use **automatic** for a controlled recovery trial after the healthy baseline exists.
4. Apply a fault from **Controlled experiments**, or use the command line below.
5. Inspect the incident timeline. An action enters **VERIFYING** after the Kubernetes call; wait for **RESOLVED** or **ESCALATED**.
6. Click **Stop new recovery actions** when finished. This changes mode to observe; verification of an action already underway continues.
7. Restore the demo with `none` between trials. Allow the five-minute cooldown before another automatic action.

### Fault choices

| Fault | Mechanism | Expected interpretation |
| --- | --- | --- |
| `errors` | `/work` returns HTTP 500 while probes remain healthy | Bad revision with a known healthy baseline can trigger rollback |
| `cpu` | CPU work added to each request | Sustained CPU and latency can trigger scale to at most three replicas; outcome depends on load |
| `memory` | Allocates 2 MiB every five seconds per faulty process | Stable growth may trigger replacement of the highest-memory ready pod; the new pod still has the faulty template |
| `none` | Restores normal fault setting and two desired replicas | Manual reset for the next trial |

### Command-line fault injection

The API and script paths both patch the same demo Deployment. The API path is available in Streamlit. The script also appends an experiment record to ignored `data/experiments.jsonl`.

```powershell
docker compose run --rm worker python scripts/experiment.py errors
docker compose run --rm worker python scripts/experiment.py none
```

For an end-to-end automated rollback smoke run, wait for the baseline and then run:

```powershell
docker compose run --rm api python scripts/smoke.py
```

The smoke script temporarily enables automatic mode, injects `errors`, waits up to five minutes for a new faulty-revision incident, restores the prior mode and normal fault in a `finally` block, and saves its outcome under ignored `data/live-smoke*.json`. Inspect cleanup errors if a run fails. A successful run validates one local path, not a reliability percentage.

## Reproducible load and measurements

Setup applies background traffic at roughly five requests per second. For a measured run, first stop that traffic so it does not confound the request count:

```powershell
kubectl --context kind-heal-lab -n heal-demo scale deployment/traffic --replicas=0
docker compose run --rm worker python scripts/load.py --url http://heal-lab-control-plane:30080 --seconds 900 --rps 5 --seed 42 --output data/trial-01.jsonl
docker compose run --rm api python scripts/report.py data/trial-01.jsonl
```

`load.py` writes one JSON line per request with timestamp, latency, and status; transport failures use status `0`. `report.py` prints request count, failures, median and approximate p95 latency. Use a unique output name for every trial. Restore background traffic when needed:

```powershell
kubectl --context kind-heal-lab -n heal-demo scale deployment/traffic --replicas=1
```

For experiments, keep the load seed, rate, duration, initial replica count, cooldown, and fault timing comparable across observe and automatic runs. Preserve failed runs. See [ML and evaluation](ML_AND_EVALUATION.md) for a comparison protocol.

## Tests, build, and inspection

```powershell
docker compose run --rm api pytest -q
docker compose logs --tail=100 worker
docker compose logs --tail=100 api
kubectl --context kind-heal-lab -n heal-demo get deployments,pods
```

After changing controller, console, scripts, or tests copied into the shared image:

```powershell
docker build -f Dockerfile.control -t heallab-control:local .
docker compose up -d
```

For a demo application change, rerun `scripts/setup.ps1` so the demo image is rebuilt, loaded into kind, and the manifests are applied. Rebuilding a Docker image alone does not replace pods already running the old local image.

`scripts/check_actions.py` directly tests scale and targeted pod replacement against the live demo and writes `data/action-check.json`. It mutates the workload and is an integration check of the tools, not a controller-policy trial:

```powershell
docker compose run --rm worker python scripts/check_actions.py
```

Start it only from the normal two-replica baseline, without a concurrent automatic experiment.

## Data and credentials

`data/incidents.db` persists settings and incident timelines. `data/kubeconfig` contains a short-lived controller token. `data/model.joblib`, load files, datasets, and trial reports are also local artifacts. The directory is ignored by Git. Do not commit tokens, kubeconfigs, `.env`, model data, or trial outputs by accident. Prometheus data is ephemeral and has six-hour/256 MB retention; export what an experiment needs before replacing its pod. The worker is single-instance only.

## Troubleshooting

| Symptom | Check and response |
| --- | --- |
| Console says telemetry stale | Inspect `docker compose logs worker`, `/status`, demo pods, Prometheus pods, and traffic. Recovery blocks stale observations. |
| Worker reports Kubernetes authentication error | The service-account token may have expired. Rerun `scripts/setup.ps1`; it renews the token and restarts API and worker. |
| No rollback baseline | Keep normal traffic running and wait for a fully rolled-out, healthy revision for at least 90 seconds. Check errors, ready replicas, and telemetry freshness. |
| Error fault creates no automatic rollback | Confirm **Apply mode** was clicked, baseline exists, mode is `automatic`, cooldown has elapsed, and the incident's policy event. |
| Action says success but incident escalates | Inspect subsequent metrics and the incident events. Kubernetes mutation success does not prove application recovery. |
| CPU or memory fault has no diagnosis | Rule thresholds and sustained observation windows may not be met. Increase controlled load only within the demo setup and inspect metric graphs. |
| API works but UI is unavailable | Check `docker compose ps` and `docker compose logs console`; API health alone does not establish console health. |

## Stop and resume

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop.ps1
```

This stops Compose services and the kind control-plane container without deleting data or images. Run setup again to resume. `docker compose down` stops the Compose services while retaining the kind cluster and incident data. Deleting the cluster with `.tools/kind.exe delete cluster --name heal-lab` is a separate, destructive cleanup step; preserve experiment outputs first.

## React workspace

`Frontend/` is the React control room, with live telemetry, incident filtering and event details, recovery mode controls, and confirmed fault injection. It runs separately from Compose and proxies requests to the existing FastAPI service. Start the backend with the normal setup procedure, then run:

```powershell
cd Frontend
bun install
bun dev
```

Open `http://localhost:5173`. The Bun server binds to localhost and forwards `/control/*` to `http://127.0.0.1:8000`; set `CONTROLLER_URL` before starting Bun to use a different API address. `PORT` can override 5173. The UI refreshes every five seconds while visible, displays connection failures, and disables mutations while disconnected. Recovery mode and fault changes require confirmation. Streamlit remains available on port 8501.

The workspace scrolls independently within the visible browser height. Scrollbar rails are hidden; use the wheel, touch, or focus the workspace and press Page Down/End to navigate. Short windows keep the sidebar and dialogs independently scrollable. Controls use shadcn Button/Select; React Bits AnimatedContent and live metric transitions use GSAP with reduced-motion support.

Run `bun run build` in `Frontend/` to verify the browser bundle. `bun start` serves the application and API proxy in production mode; a static `dist/` host alone does not supply the proxy. Browser checks on 19 November 2026 covered incident details, mode updates, fault cancellation, and a 390 px layout using temporary test responses. The live API was unavailable during these checks; cluster recovery was not exercised.
