# HealLab implementation

The report's core idea is implemented as a local, observable recovery loop. Kubernetes runs the demo workload; the Python controller runs outside that cluster. Prometheus provides measurements, Streamlit provides incident controls and Grafana provides metric dashboards.

## What works

- Application request, error, latency, CPU and memory telemetry, plus Kubernetes replica state.
- Sustained rule detection, evidence-based diagnoses, bounded rollback, scaling and pod replacement.
- Persisted incident and action timelines, observe/automatic modes and a stop-new-actions control.
- Verification against real application traffic, not merely successful Kubernetes API calls.
- Worker restart reconciliation without replaying pending actions.
- Optional Isolation Forest evidence and stable-trend memory-limit forecasting.
- Controlled faults, reproducible traffic, training/validation tools and exported test results.

## Live checks on 18 November 2026

- Faulty revision detected approximately 74 seconds after injection.
- Controller automatically restored the healthy revision.
- Incident resolved approximately 167 seconds after injection, after three healthy observations.
- Scaling from two to three replicas and targeted pod replacement passed separate tool integration checks. These are tool checks, not proof that every overload or memory leak is automatically cured.
- Streamlit rendered against the actual API with six metric cards and no UI exceptions.
- Grafana's provisioned Prometheus data source returned live metrics.
- 24 unit/component tests passed, including API, policy, adapter, worker restart and UI checks.

Raw evidence is retained in ignored local artifacts `data/live-smoke.json` and `data/action-check.json`.

## Initial ML baseline

An Isolation Forest model was trained from 44 real healthy Prometheus windows. Ten later healthy windows calibrated its threshold, with a 75-second gap to avoid overlapping rate windows. The known fault interval and its following one-minute telemetry window were excluded.

In a descriptive replay, the model flagged 2 of 5 available faulty-revision windows. This is a weak initial result, not a general accuracy estimate. The deterministic diagnostic rules remain responsible for identifying and recovering faulty deployments. Live inference is active, and the model version and score are available in `/status` and the console.

The model, datasets, provenance and replay counts are stored in `data/model.joblib`, `data/bootstrap-*.jsonl`, `data/model-provenance.json` and `data/model-evaluation.json`. The calibration windows are not an independent test set. More independent traffic patterns and repeated fault experiments are needed before making an accuracy claim.

Two normal-load runs completed 893 and 1,778 measured requests, respectively, with no failures and p95 latency around 30 ms. Background demo traffic also continued during these runs.

## Limits of the current evidence

One real automatic rollback is a functional smoke test, not a statistical reliability benchmark. The anomaly model is an exploratory baseline until evaluated across separate normal/fault runs. Memory forecasts cover stable memory growth only. Memory-leak restart is mitigation and can recur. Scaling may not solve application bugs or unavailable dependencies.

The system uses one small local cluster to fit an 8 GB machine. No real multi-cloud failover, production access controls, external LLM dependency, HPA benchmark or five-trial-per-scenario research evaluation is claimed.

## Reproducibility

Use the setup and demo commands in the root README. Keep load seeds and traffic settings identical when comparing Kubernetes-only (observe mode) with automatic recovery. Export each load run separately. Preserve complete experiment runs for train/validation/test separation, and report failed recovery as escalation rather than excluding it.
