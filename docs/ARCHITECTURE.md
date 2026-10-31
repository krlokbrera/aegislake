# Architecture and engineering decisions

## Scope

The system is an offline batch reference for identity telemetry. It provides a local runnable vertical slice and an Azure-compatible deployment path. Its interfaces are canonical JSONL in, partitioned Parquet and evidence-rich JSON out.

## Boundaries and contracts

| Boundary | Contract | Failure behavior |
| --- | --- | --- |
| Source → bronze | UTF-8 JSONL; one object per line | Snapshot first; malformed lines quarantined |
| Bronze → silver | Required identifiers, aware timestamp, strict booleans and nullable MFA | Reject incompatible records; retain line references |
| Event identity | Same event_id and same canonical content | Duplicate counted once |
| Identity conflict | Same event_id, changed content | First accepted record retained; later conflict quarantined |
| Silver → features | Closed 15-minute windows; UTC | Fail if numerical features are not finite |
| Features → benchmark | Complete labels; nonempty temporal partitions | Fail explicitly, rather than silently inventing labels |
| Validation → selection | Both labeled classes | Reject one-class calibration |
| Scoring → queue | Threshold plus per-day top-k | Stable deterministic tie-break |
| Human feedback | Known alert identifier and bounded decision values | Reject unknown cases |
| Azure publication | Verified synthetic benchmark run | Reject real-data runs and arbitrary destination URLs |

## Lake layout

Bronze is a per-run byte snapshot. Silver partitions by UTC event date. Gold separates feature tables, alerts and reports. Quarantine stores line numbers and bounded validation reasons, while original payloads remain only in bronze.

The hash-derived run folder supports repeatable experiments. Artifacts are prepared in a staging directory and renamed on completion. This is an atomic publication pattern on one filesystem, not a distributed transaction across services.

Source files are snapshotted in chunks, but the accepted event table, historical references and SQL aggregation operate in memory. The project does not stream an unbounded enterprise log feed.

## Time semantics

A window with start 10:00 and end 10:15 is scoreable after 10:15. Source fanout uses all events in that same closed window. That would be look-ahead if the system claimed to score at 10:01; it does not.

Train/validation/test boundaries align to UTC midnights and preserve whole windows. The destination reference is learned from the training period and stays fixed. Training rows therefore use a retrospective training reference; validation and test never contribute to it. For an online deployment, implement a versioned historical feature store and replay before making latency claims.

AegisLake assumes the supplied batch is complete. Watermarks, event arrival times, late-event correction and replay after partial source delivery are future work.

## Components

- `contracts.py`: event shape, type checks and UTC normalization.
- `lake.py`: snapshotting, deduplication, quarantine and Parquet output.
- `features.py`: explicit SQL feature construction.
- `models.py`: baselines, hybrid ranking and evidence templates.
- `evaluation.py`: validation-only thresholds, operational metrics and drift diagnostics.
- `pipeline.py`: run identity, execution and lineage.
- `scoring.py`: future-batch inference from checked reference data, without pickle.
- `review.py`: local analyst decisions.
- `azure.py` and `cloud_job.py`: optional private report publication.
- `report.py`: escaped, self-contained investigation view.

## ADR 001: Parquet and DuckDB first

Choice: use pandas for orchestration, Arrow/Parquet for storage, DuckDB for SQL.

Reason: a reviewer can reproduce the complete pipeline on a laptop. SQL and storage choices remain portable to larger platforms.

Consequence: single-node memory is a limit. A Spark implementation is justified only by measured volume or a specific role requirement. A future Spark port must reproduce the feature contract and temporal boundaries on the same fixture.

## ADR 002: Multiple baselines

Choice: compare rules, Isolation Forest, logistic regression and a fixed hybrid.

Reason: machine learning must be compared against an understandable alternative. Model complexity is useful only when it improves an agreed objective.

Consequence: labels influence the supervised model and validation selection. This is not a fully unsupervised evaluation, even though one candidate is an anomaly detector.

## ADR 003: No serialized executable models

Choice: store training features, seed, configuration and dependency versions, then reconstruct the small model for future batch scoring.

Reason: this avoids accepting arbitrary pickle files.

Consequence: inference has startup training cost; exact dependency versions must match the reference. For a service, a reviewed safe model format, signing, immutable model registry and reproducibility tests should replace reconstruction.

## ADR 004: Finite Azure jobs

Choice: optional manual Container Apps Job; no scheduled background workload.

Reason: the demonstration has a finite execution boundary and can stop consuming compute.

Consequence: outputs must be uploaded before container storage disappears. The sample job publishes only synthetic reports. Storage operations and other Azure services can still incur charges.

## ADR 005: Human decisions remain separate

Choice: record review decisions, never remediate identities.

Reason: the output is evidence for investigation and model analysis.

Consequence: escalation, account disablement and credential reset remain external analyst processes; no permissions for them are requested.
