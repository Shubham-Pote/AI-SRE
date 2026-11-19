# Current status, limitations, and roadmap

## What is implemented now

| Area | Current capability | Evidence boundary |
| --- | --- | --- |
| Local deployment | Setup/resume scripts, kind cluster, demo workload, monitoring, Compose API/worker/console/Grafana | Designed and locally exercised on one Windows/Docker Desktop host |
| Telemetry | Request rate, error fraction, p95 latency, CPU, memory, readiness, desired replicas, revision, scrape freshness | One instrumented demo application; not arbitrary workloads |
| Diagnosis | Sustained rules for bad revision, memory trend, CPU/latency overload, unknown errors/degradation | Thresholds are fixed in code and need scenario calibration |
| Automatic recovery | Verified-template rollback, scale by one up to three, targeted highest-memory ready pod replacement | One attempt per incident, five-minute cooldown, single namespace/workload |
| Safety | Observe mode, fresh-data checks, action allowlist, RBAC, post-action verification, restart reconciliation | Local API has no multi-user access control |
| Incident record | SQLite incident/event timeline and console display | Latest 200 incidents exposed through API; no export/retention service |
| ML | Optional Isolation Forest anomaly evidence and manual-review escalation; memory trend forecast | Exploratory baseline, no validated predictive accuracy or ML-driven actuation |
| Interfaces | React control room, Streamlit console, provisioned Grafana dashboard, FastAPI docs | React runs separately on port 5173; successful UI workflows were checked with browser fixtures while the live API was unavailable |
| Validation tools | Unit/component tests, live smoke, action check, seeded load, reports, dataset collection/training | Three saved local smoke trials (two resolved, one escalated) and tool checks are not a comparative benchmark |

The [ML and evaluation guide](ML_AND_EVALUATION.md#evidence-recorded-so-far) records the 18 November 2026 integration checks: 24 passing tests, a first observed automatic rollback, and the later saved smoke trials. The ignored local `data/live-smoke-*.json` files record three trials from that date: two verified resolutions and one `unknown_errors` escalation with no supported automatic action. The exact current test and cluster state should be checked again before a demonstration or report update.

## Known limitations and risks

1. **Scope:** one kind cluster, one namespace, one known Deployment, and one worker. Multi-cluster routing, cloud failover, production service discovery, and HA worker coordination are not implemented.
2. **Security:** localhost-bound API with no authentication, anonymous Grafana Viewer, and a 24-hour controller token that setup must renew. The system is for an isolated local demo.
3. **Diagnosis coverage:** only a few hard-coded fault patterns. A changed revision is required for automatic error rollback; unknown errors and model-only anomalies need manual review. Fixed thresholds may misclassify different workloads.
4. **Recovery limits:** scale-out can fail when the bottleneck is shared or the code is faulty. Pod replacement does not repair a memory leak in the image and may be followed by recurrence. A verified baseline is needed for rollback.
5. **Telemetry dependence:** Prometheus scrape gaps, lack of traffic, stale rates, or unavailable Kubernetes state prevent action. That is intentional for safety but limits availability during observability failures.
6. **Model evidence:** the model was trained on a small local healthy sample. Calibration is not a final independent test. The reported two-of-five fault-window replay cannot support sensitivity, precision, or generalization claims.
7. **Experiment evidence:** two successful rollback smoke trials, one escalated trial, and action checks demonstrate behavior and a limit of diagnosis. Five independent trials per scenario, matched controls, HPA comparison, and cloud validation remain to be done.
8. **Persistence and scale:** SQLite is appropriate for the single local worker; no distributed coordination, backups, migration tooling, or long-term retention are implemented. Recent in-memory history is lost on worker restart, though incidents persist.
9. **Frontend:** the React control room connects to FastAPI through a local Bun proxy, but is not included in Compose. Live end-to-end validation with the running cluster remains necessary; browser fixture tests verify interaction behavior only.

## Next goals, in priority order

### Milestone 1 — Reproducible local evaluation

- Define a trial manifest with scenario, mode, fault time, load seed/rate, environment version, and outcome.
- Run repeated observe-versus-automatic trials for the bad revision; extend to CPU and memory with explicit success criteria.
- Preserve all trial artifacts, including escalations and failed setup/cleanup. Produce tables and plots for detection, verified recovery, request failures, and latency.
- Add an HPA baseline only after the manual scaling scenario is reproducible under comparable requests, limits, and load.

**Done when:** another person can run the protocol and reproduce the outcome calculation without selecting favorable trials.

### Milestone 2 — Stronger diagnosis and model validation

- Gather independent healthy patterns and fault runs, with train/validation/test separation by run and nonoverlapping rate windows.
- Report anomaly confusion matrix, false alarm rate, detection delay, and confidence intervals where sample size permits.
- Calibrate rule thresholds against workload behavior, document tradeoffs, and add regression tests for newly supported cases.
- Decide whether an ML-informed policy is justified. Any such policy must retain explicit action allowlists, freshness, cooldown, limits, and post-action verification.

**Done when:** model claims are backed by an independent test set and any decision benefit is measured against the same rule-based controller.

### Milestone 3 — Control room and operational hardening

- Validate the implemented React control room against a running cluster and decide whether to include it in Compose or keep it as a separate development service.
- Add a clear distinction among detected, observed, executing, verifying, resolved, and escalated incidents; handle stale telemetry and API errors in the UI.
- Add API identity and authorization before any shared deployment, plus audit attribution, credential rotation, and safer experiment permissions.
- Define data retention, backups, and migration strategy if moving beyond a local prototype.

**Done when:** an operator can understand evidence and action outcome, and the control surface is safe for its intended deployment context.

### Milestone 4 — Broader infrastructure research

- Generalize workload configuration and adapter boundaries only after the one-workload behavior is measured reliably.
- Test a second workload or cluster, then study coordination and state storage for more than one worker.
- Evaluate cloud or multi-cluster recovery in a controlled test environment, with explicit permissions, cost limits, and failure-domain definitions.

**Done when:** claims of portability or multi-cluster support are demonstrated by actual tests rather than inferred from code structure.

## Intended final outcome

The eventual project aims to be an **evidence-driven infrastructure recovery system** that detects user-visible degradation, explains a supported cause, chooses a bounded action, records why it was allowed, and verifies whether service actually recovered. The research contribution should include a reproducible comparison against observe-only operation and relevant platform automation, plus an honest assessment of when ML helps or does not help. Production security, broad workload support, and cloud failover require separate implementation and validation before they can be claimed.
