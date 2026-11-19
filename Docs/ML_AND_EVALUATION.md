# ML, forecasting, and evaluation

## Current role of ML

HealLab has two distinct analytical paths:

1. **Deterministic diagnostic rules** identify supported conditions and propose rollback, scaling, pod replacement, or manual review. These rules authorize an automatic action only after safety checks.
2. **Optional Isolation Forest** scores each observation against a trained healthy baseline. Its anomaly flag, score, and model version are displayed and attached to incidents. Three consecutive model anomalies without a supported rule diagnosis create a manual-review incident. The model never authorizes a recovery action on its own.

If `data/model.joblib` is absent, rule-based monitoring and recovery continue. A model loading or inference error is reported in telemetry as `model_error`; it does not grant permission to act. `controller/ml.py` loads the model for each inference. The feature vector is request rate, error fraction, p95 latency, memory divided by limit, CPU, and ready replica count.

## Memory-limit forecast

The forecast in `controller/core.py` is a linear trend estimate, not the Isolation Forest. It fits recent memory observations, rejects gaps, flat or decreasing trends, and low fit quality, then estimates seconds until the configured memory limit. The memory diagnosis also requires memory usage above 55% of that limit and an estimated time below five minutes. A restart or pod replacement may temporarily lower observed memory while the faulty code remains, so successful mitigation must be verified and recurrence should be recorded.

## Collect and train a model

Collect **separate healthy runs** with consistent normal traffic. `collect.py` samples every 15 seconds. `train.py` requires at least 40 training windows and 10 validation windows, rejects a validation file reused as a training file, fits 100 Isolation Forest estimators with seed 42, and calibrates the anomaly threshold from the 1st percentile of validation scores.

```powershell
docker compose run --rm worker python scripts/collect.py --output data/train-run-01.jsonl --windows 60
docker compose run --rm worker python scripts/collect.py --output data/validation-run-01.jsonl --windows 20
docker compose run --rm worker python scripts/train.py --train data/train-run-01.jsonl --validation data/validation-run-01.jsonl
```

The resulting bundle is `data/model.joblib`. Use complete, independent runs rather than splitting neighboring windows at random: the features include one-minute rates, so adjacent observations share raw requests. The training script checks file identity and minimum size, but **the researcher must ensure** the runs are truly independent and healthy. It does not perform full experimental leakage detection.

For an exploratory baseline, `scripts/bootstrap_model.py` queries the last hour of Prometheus at 15-second steps, selects healthy low-CPU/low-memory windows, excludes known smoke fault intervals and one minute afterward, and separates ten late validation points from training by more than a minute. It requires at least 55 healthy windows before filtering and 40 training windows after the gap. It writes datasets and provenance in `data/`.

```powershell
docker compose run --rm worker python scripts/bootstrap_model.py
```

This is useful for confirming the inference pipeline with real telemetry. Its holdout is still drawn from the same general local run and is **not an independent fault test**.

## Evidence recorded so far

The local integration check on **18 November 2026** recorded a faulty-revision rollback: detection about 74 seconds after injection and verified resolution about 167 seconds after injection. Separate live tool checks passed for scaling from two to three replicas and targeted pod replacement. Streamlit rendered against the live API with six metric cards, Grafana returned live Prometheus data, and 24 unit/component tests passed at that time. These are historical observations; rerun the checks for the present environment. The first rollback is preserved in ignored `data/live-smoke-1794999345.json`, and the action check in `data/action-check.json`. `data/live-smoke.json` is overwritten by each new smoke run.

The ignored local `data/live-smoke-*.json` artifacts currently contain **three** smoke trials from 18 November 2026. Two resolved after verified rollback, with detection/recovery times of about **73.9/167.3** and **84.7/176.7** seconds. One trial escalated: it was diagnosed as `unknown_errors`, its policy event said `No supported automatic action`, and no automatic recovery was claimed. This failed trial is part of the evidence. Three trials with different outcomes still do not constitute a controlled reliability estimate.

An exploratory Isolation Forest baseline used 44 real healthy Prometheus windows for training and ten later healthy windows for threshold calibration, with a 75-second gap. In a descriptive replay, it flagged two of five available faulty-revision windows. That tiny, selected replay is **not** an accuracy estimate. Two recorded normal-load runs had 893 and 1,778 measured requests with no failures and p95 latency around 30 ms; background traffic also ran, so those counts do not represent all service traffic.

The raw artifacts are in ignored `data/` when present. If they are missing from a checkout, treat these values as reports of earlier local runs and reproduce them before claiming a current result.

## Evaluation design for the next phase

### Questions

- Does automatic rule-based recovery reduce time to verified service restoration against **observe-only Kubernetes behavior** under the same fault and traffic pattern?
- How often does each supported diagnosis lead to a verified recovery, an escalation, or an unsafe/incorrect action?
- Does the anomaly model identify independent faults while keeping false alarms low on independent normal workloads?
- Does scaling improve a genuine overload, and how does it compare with Kubernetes HPA under matched resource limits and traffic?

### Trial protocol

1. Define scenarios and expected outcome before running them: bad revision, CPU overload, memory growth, and at least one unsupported or ambiguous condition.
2. Establish a clean healthy baseline, two desired replicas, fresh metrics, and the same load seed/rate/duration for each paired condition.
3. Run observe mode and automatic mode separately. Record the exact fault injection time, traffic file, incident timestamps, action events, verification outcome, configuration, and any manual intervention.
4. Restore the workload between trials, respect the five-minute action cooldown, and rerun the healthy baseline period.
5. Repeat independent trials; the current README proposes **five per scenario**. Preserve failures and aborted trials with reasons instead of discarding them.
6. Keep training, validation, and final test runs separate by complete experiment run. Exclude fault and post-fault rate windows from healthy training data.
7. Report distributions and uncertainty, not only a best run or one median. Describe whether background traffic was enabled in each trial.

`scripts/load.py` saves request-level JSONL; `scripts/report.py` summarizes requests, failures, median, and approximate p95 latency. `scripts/smoke.py` saves a functional rollback trial; `scripts/summarize_recovery.py` aggregates preserved smoke files and writes `data/recovery-summary.json`. The summary is labeled functional smoke evidence and does not by itself produce a randomized comparison.

### Suggested outcome measures

| Measure | Definition or caution |
| --- | --- |
| Detection delay | Incident creation time minus fault injection time |
| Action delay | First action event time minus incident creation time |
| Verified recovery time | Resolution time minus fault injection time; report escalations separately |
| User-visible impact | Failed request count/rate and latency distribution from load files |
| Recovery success | Fraction of trials resolved after verification, with the trial denominator shown |
| False alarm | Incident or anomaly under an independently healthy run |
| Action safety | Wrong-workload mutations, actions with stale evidence, cooldown/limit violations |

The current ML score supplies evidence, not a distinct actuation policy. Therefore an observe-versus-automatic recovery comparison tests the **rule-based controller**. Do not attribute a recovery-time improvement to ML without implementing and separately testing a policy in which the model changes a decision, while retaining the safety boundary.
