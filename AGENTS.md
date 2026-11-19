# Repository Guidelines

## Project Structure & Module Organization

HealLab is a local infrastructure monitoring and recovery prototype using Python 3.12 containers.

- `controller/`: FastAPI endpoints, SQLite persistence, telemetry adapters, recovery policies, worker orchestration, and ML inference. Keep decision logic in `core.py` separate from Kubernetes operations in `adapters.py`.
- `demo/`: instrumented FastAPI application with controlled faults.
- `console/`: Streamlit interface; `.streamlit/` contains its theme.
- `infra/`: Kubernetes manifests and Grafana dashboard/provisioning assets.
- `scripts/`: setup, shutdown, load generation, experiments, training, and reporting.
- `tests/`: pytest suites; `Docs/`: the maintained project documentation and Stage 1 report.
- `data/`: ignored runtime database, credentials, models, and experiment results.

## Build, Test, and Development Commands

Run commands from the repository root with Docker Desktop's Linux engine running.

- `powershell -ExecutionPolicy Bypass -File scripts/setup.ps1`: create or resume the cluster, build images, renew credentials, and start services.
- `docker build -f Dockerfile.control -t heallab-control:local .`: rebuild the shared controller/console image after source changes.
- `docker compose up -d`: apply the rebuilt image to services.
- `docker compose run --rm api pytest -q`: run component and UI tests.
- `docker compose run --rm api python scripts/smoke.py`: inject a faulty revision and verify automatic recovery against the demo cluster.
- `powershell -ExecutionPolicy Bypass -File scripts/stop.ps1`: stop services and the cluster without deleting data.

Streamlit runs on port 8501, Grafana on 3000, and API documentation on 8000 at `/docs`.

## Coding Style & Naming Conventions

Use four-space Python indentation, `snake_case` functions/modules, and `PascalCase` classes. Use two-space YAML indentation. Prefer typed records and small, testable policy functions. No formatter or linter is currently configured; avoid unrelated formatting changes.

## Testing Guidelines

Name tests `tests/test_*.py` and functions `test_*`. Use pytest fixtures, mocked Kubernetes calls, and Streamlit `AppTest`. Add regression tests for changed recovery decisions, stale telemetry, baseline promotion, and restart handling. No numerical coverage threshold is configured. Record live experiments separately from unit-test results; preserve failed trials and avoid training/test leakage.

## Documentation Maintenance

Treat `Docs/README.md` as the documentation index and keep the existing focused guides as the canonical structure: architecture, recovery policy, operations, API reference, ML and evaluation, and status and roadmap. Update the relevant guide when implementation, commands, thresholds, interfaces, evidence, limitations, or plans change; update the index if a guide is added or renamed. Keep the root `README.md` brief and point readers to `Docs/README.md` for detail. Avoid parallel implementation notes, duplicate demo guides, or dated status files when the information belongs in a canonical guide. Preserve formal academic reports as separate deliverables. Distinguish implemented behavior from locally observed evidence and planned work, date experimental results, include failed trials, and check internal links after documentation edits.

## Commit & Pull Request Guidelines

History contains only `First Pushover`, so no established commit convention exists. Use concise imperative subjects, such as `Fix baseline promotion during rollout`. PRs should explain behavior changes, relevant issues, validation commands/results, and limitations. Include screenshots for interface changes.

## Configuration & Recovery Boundaries

Never commit `data/`, `.env`, tokens, or kubeconfigs. Keep experiments scoped to `kind-heal-lab` and `heal-demo`. Preserve action allowlists, cooldowns, replica limits, and post-action verification. ML scores alone must not authorize recovery.
