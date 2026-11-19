# HealLab documentation

HealLab is a local research prototype for observing a Kubernetes workload, diagnosing a small set of failures, taking bounded recovery actions, and verifying the result from application traffic. This documentation describes the repository as implemented, including experimental evidence and work that remains.

## Reading guide

| Document | Use it for |
| --- | --- |
| [Architecture](ARCHITECTURE.md) | Components, data flow, persistence, deployment boundaries, and code map |
| [Recovery policy](RECOVERY_POLICY.md) | Diagnostic rules, safeguards, action lifecycle, and theoretical rationale |
| [Operations](OPERATIONS.md) | Setup, UI and API actions, fault experiments, troubleshooting, and shutdown |
| [API reference](API_REFERENCE.md) | Implemented endpoints, request bodies, responses, and local API limitations |
| [ML and evaluation](ML_AND_EVALUATION.md) | Anomaly model, memory forecast, experiment method, metrics, and evidence quality |
| [Status and roadmap](STATUS_AND_ROADMAP.md) | Implemented features, limitations, next milestones, and final project aim |

The root [README](../README.md) is the quick start. The five-minute presentation walkthrough is in [Operations](OPERATIONS.md#five-minute-demonstration). The formal Stage 1 report remains in `Project Stage 1 Report.docx` as an academic deliverable.

## Evidence labels used here

- **Implemented:** the behavior exists in source code, manifests, or tests.
- **Locally observed:** a dated run is described in [ML and evaluation](ML_AND_EVALUATION.md); its raw artifacts are under ignored `data/` and may be absent from a fresh checkout.
- **Planned:** a goal or experiment, not a current capability.

These distinctions matter especially for ML accuracy, recovery reliability, cloud support, and comparative results. A successful smoke test establishes that one path works in the local demo; it does not establish a general success rate.
