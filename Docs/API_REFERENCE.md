# Local control API

The FastAPI app in `controller/api.py` is published at `http://localhost:8000`; interactive OpenAPI documentation is at `http://localhost:8000/docs`. It is designed for local demonstration and has no user authentication or authorization layer. Avoid exposing it on a shared network. Compose binds its published port to localhost.

## Endpoints

| Method and path | Purpose | Notes |
| --- | --- | --- |
| `GET /health` | API liveness and last worker error | `status: ok` means the API responds; inspect `worker_error` and `/status` for monitoring health |
| `GET /status` | Current mode, latest telemetry, stale flag, worker error, baseline availability | `stale` is true if latest stored observation is older than 45 seconds |
| `PUT /mode` | Set recovery mode | Body `{"mode":"observe"}` or `{"mode":"automatic"}`; invalid values return 422 |
| `GET /telemetry/history` | Recent observation records | Worker stores at most 60 observations |
| `GET /incidents` | Newest incident summaries | Maximum 200, descending ID |
| `GET /incidents/{id}` | One incident plus ordered events | Unknown ID returns 404 |
| `POST /experiments` | Patch a demo fault | Body `{"fault":"none"}`, `errors`, `memory`, or `cpu`; invalid values return 422; Kubernetes errors return 503 |
| `GET /experiments` | Last experiment submitted through the API | Script-based fault injection records separately in `data/experiments.jsonl` |

The experiment endpoint changes only the configured demo Deployment in `heal-demo`. Setting `none` restores the `good` revision marker, sets desired replicas to two, and clears the deduplication condition. It does not delete incident history. An `errors` fault returns HTTP 500 from `/work` while health/readiness probes still answer, demonstrating why request telemetry matters.

## Examples from PowerShell

```powershell
Invoke-RestMethod http://localhost:8000/status
Invoke-RestMethod http://localhost:8000/incidents
Invoke-RestMethod -Method Put -Uri http://localhost:8000/mode -ContentType application/json -Body '{"mode":"observe"}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/experiments -ContentType application/json -Body '{"fault":"errors"}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/experiments -ContentType application/json -Body '{"fault":"none"}'
```

For a recovery demonstration, wait for fresh telemetry and `baseline_ready: true`, then select automatic mode, inject `errors`, and inspect the resulting incident and events. Do not treat `GET /health` alone as proof that the worker, Prometheus, or demo workload is healthy. See [Operations](OPERATIONS.md) for the full sequence.

## Current API boundaries

The API has no multi-user identity, audit attribution, rate limiting, or approval workflow. It does not offer arbitrary cluster, namespace, or workload selection. It returns the latest saved worker observation rather than querying Prometheus on demand. These are deliberate prototype boundaries, not production guarantees.
