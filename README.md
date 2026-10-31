# AegisLake

> Verified dashboard release 0.2.0: 74 tests pass with 90% measured Python coverage. [Release evidence](https://github.com/krlokbrera/aegislake/actions/runs/41227547021).

## Interactive SOC dashboards

The web interface now includes a native dashboard with linked activity charts, ATT&CK distribution,
a UTC weekday/hour heatmap, top identities and score distributions. Selecting a chart filters every
KPI and the investigation queue. It reads actual AegisLake run outputs, with explicit synthetic,
labeled-evaluation or unlabeled-scoring provenance.

```bash
aegislake demo --seed 7 --output runs
aegislake serve --runs runs --port 8767
# Open http://127.0.0.1:8767/dashboard.html
```

The local read-only API discovers completed batches without restarting. Optional 30-second polling
can follow the latest batch, while manual refresh preserves filters for the current batch. Scoring
batches get their own dashboard without inherited precision/recall. Each run also includes a
self-contained `dashboard.html`, browser-local JSON import and a portable filtered JSON export.
This release does not connect to a live SIEM tenant or deploy an Internet-facing web service.
See the [dashboard guide](docs/DASHBOARDS_ES.md) for data integration, API routes and limits.

**Identity threat analytics: security data engineering, reproducible machine learning, and human-led investigation.**

A portfolio project by Carlo Alessandro Cabrera. AegisLake turns authentication events into a small security data lake, compares detection methods under an analyst workload budget, and produces an offline investigation dashboard.

> Previous release 0.1.2: 49 tests passed with 91% measured coverage; dependency audit, Bicep build and non-root Docker execution passed. [Execution evidence](https://github.com/krlokbrera/aegislake/actions/runs/41222003014). Live Azure deployment remains pending.

[Spanish guide](docs/GUIA_ES.md) · [Research and design](docs/RESEARCH_ES.md) · [Azure](docs/AZURE.md) · [Model card](docs/MODEL_CARD.md) · [Data card](docs/DATA_CARD.md) · [Interview walkthrough](docs/CV_AND_INTERVIEW_ES.md)

## Why this project

A suspicious login is useful only if an analyst can investigate it. This project treats detection as a data product: reliable ingestion, explicit data contracts, temporal evaluation, traceable evidence, and bounded review workload. It combines the data engineering and cybersecurity experience that a generic classification notebook usually separates.

| Capability | Implemented evidence |
| --- | --- |
| Data engineering | Bronze snapshot, validated silver Parquet partitions, SQL feature aggregation, gold outputs |
| Analytics | Daily SOC KPIs, quality reconciliation, feature drift diagnostics, offline report |
| Applied AI | Rules, Isolation Forest, logistic regression, hybrid score, validation-only model selection |
| ML evaluation | Train/validation/test by time; average precision; precision/recall; false positives; daily capacity |
| Security | Keyed pseudonymization, no model pickle loading, private Blob access, no keys in code |
| Human oversight | Evidence summaries and a local append-only-at-application-level review ledger |
| Azure engineering | Bicep, optional finite Container Apps Job, managed identity, scoped RBAC |
| Delivery | Python package and CLI, Docker, tests, GitHub Actions, source-backed design documentation |

## Run the local demo

Python 3.11 or 3.12 is recommended. Run from the repository root:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[dev]"
aegislake demo --output runs
```

The CLI prints the completed run directory. Open its `report.html` in your browser. It is a self-contained, offline dashboard with workload charts, model comparisons, searchable evidence and paginated alerts. Open the linked `mitre.html` page to explore the curated ATT&CK map and jump to alerts filtered by technique. Keep the HTML pages and their `attack-mapping.json` and `dettect-techniques.yaml` downloads together. Alerts expose candidate tactic IDs as well as technique IDs. [DeTT&CT integration and scoring scope](docs/DETTCT_ES.md).

Default workload: 30 days, 50 identities, seed 42, 18 training days, six validation days, six test days, and at most 25 queued user windows per test day. These are simulator settings, not organization-wide capacity recommendations.

```bash
pytest --cov=aegislake --cov-report=term-missing
ruff check src tests scripts
pip-audit --progress-spinner off
```

For Docker:

```bash
docker build -t aegislake:local .
docker run --rm -v aegis-demo:/app/runs aegislake:local
# The named volume retains output; copy it using a separate read-only container if needed.
```

## Data flow

```mermaid
flowchart TD
    A["Synthetic JSONL or canonical labeled export"] --> B["Bronze snapshot and quality checks"]
    B --> C["Silver Parquet by UTC date"]
    B --> Q["Rejected line references"]
    C --> D["Closed 15-minute SQL windows"]
    D --> E["Temporal evaluation and model selection"]
    E --> F["Gold alert queue and offline report"]
    F --> G["Analyst review ledger"]
    F --> H["Private Azure reports"]
```

The reference implementation is single-node batch processing. It does not claim streaming delivery guarantees, distributed exactly-once processing, or incident response automation.

## Useful commands

```bash
# Evaluate your canonical labeled dataset:
aegislake run --input data/labeled-events.jsonl --output runs --train-days 18 --validation-days 6

# Record a review; replace the run path and alert identifier:
aegislake review --run runs/RUN_ID --alert-id ALERT_ID --decision needs_context --reviewer analyst-01

# Adapt an existing Graph JSON export after setting AEGIS_PSEUDONYM_KEY privately:
aegislake adapt-entra --input data/graph-export.json --output data/pseudonymous.jsonl

# Score future unlabeled events from an integrity-checked reference:
aegislake score --reference runs/RUN_ID --input data/future.jsonl --output runs/future-batch

# Upload only synthetic reports after Azure login and scoped RBAC setup:
python -m pip install ".[azure]"
aegislake publish --run runs/RUN_ID --account YOUR_STORAGE_ACCOUNT
```

Synthetic-trained references require an explicit `--allow-domain-shift` for new-batch scoring. This is an experimental interoperability path, not validation on Entra telemetry.

## Outputs

Each completed run contains:

- `bronze/events.jsonl`: original snapshot, kept locally.
- `silver/event_date=.../events.parquet`: validated partitions.
- `quarantine/rejected.json` and `quality.json`: disposition accounting.
- `gold/*_features.parquet`: train, validation and test windows.
- `gold/alerts.json`: evidence queue without ground-truth labels.
- `report.html`, `mitre.html` and `report.json`: investigation dashboard, curated technique explorer, results and limitations.
- `dashboard.html` and `dashboard.json`: linked native charts, portable data snapshot and optional local API exploration.
- `manifest.json`: input hash, configuration, versions and output hashes.
- `reviews.sqlite`: created when an analyst records a decision.

Raw telemetry and outputs are ignored by Git. GitHub Actions uploads only synthetic reports, manifests, coverage and an environment record.

## Verification evidence and remaining scope

Read [VALIDATION_STATUS.md](docs/VALIDATION_STATUS.md) for observed checks and remaining limits. [A generated synthetic report](examples/demo/report.html), its JSON metrics and manifest are included for inspection. Azure student access and live deployment are pending.

## License

MIT for original project code. External datasets retain their own terms and attribution requirements. No employer or client data is included.
