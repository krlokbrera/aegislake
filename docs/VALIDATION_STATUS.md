# Validation status and evidence ledger

Prepared: 2026-10-31.

## Current evidence

| Item | Status | Evidence required to mark verified |
| --- | --- | --- |
| Primary-source research | Completed in design documentation | Sources and decisions in RESEARCH_ES.md |
| Implementation | Prepared | Source tree and review diff |
| Python runtime execution | Not yet verified | Actual pytest and CLI output from target runner |
| Lint | Not yet verified | Actual Ruff result |
| Dependency vulnerabilities | Not yet verified | Actual pip-audit result for resolved environment |
| Bicep compilation | Not yet verified | Actual az bicep build result |
| Docker build | Not yet verified | Successful image build log |
| End-to-end synthetic demo | Not yet verified | Generated report and manifest |
| Real-data validation | Not performed | Authorized benchmark, label review and backtest |
| Azure account and student credit | Not verified | Active offer and available credit in the user's tenant |
| Azure resource deployment | Not performed | What-if, deployment output and verified private blob read |
| Repository publication and PR | Pending target availability | Returned GitHub URLs and head commit |

The local execution environment became unavailable during preparation. No test pass count, measured accuracy, latency or cost has been invented. GitHub connectivity confirms account access but does not itself prove that a new repository exists or that Azure is connected.

Source preparation includes the complete implementation, regression tests, CI definition, infrastructure, and research. This file must retain pending statuses until execution is possible.

## Required first verification

1. Install the project in an isolated Python 3.11/3.12 environment.
2. Run Ruff, pytest, pip-audit and the default demo.
3. Open report.html and inspect values, escaping and layout.
4. Check split boundaries, quality counts, manifest hashes and actual daily queue volume.
5. Compile the infrastructure and build the container.
6. Archive the exact resolved dependencies with the run manifest.
7. Replace this table with observed run identifiers and links.
8. Only then use measured results in the CV.

## Explicit review work

- Confirm one temporal holdout is enough for the demonstration narrative; design multiple walk-forward folds before broader claims.
- Review whether the fixed UTC schedule and training-derived novelty reference fit a future real dataset.
- Evaluate confidence intervals and campaign-level recall.
- Produce a reviewed exact dependency lock after the first successful resolution.
- Verify Azure offer, remaining credit, regional availability and retention before provisioning.
- Verify the optional job image is publicly pullable and does not contain telemetry.

These are concrete review items; a draft PR may retain them until evidence exists. A failed CI check should be repaired on its branch and rerun before merging.
