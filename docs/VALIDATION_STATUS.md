# Validation status and evidence ledger

Release 0.1.2 verified on 2026-10-31 in an isolated GitHub Actions Python 3.12 Linux environment.

Evidence: https://github.com/krlokbrera/aegislake/actions/runs/41222003014

| Check | Observed result |
| --- | --- |
| Regression, rendering, DeTT&CT and cloud publication tests | 49 passed |
| Coverage | 91% of measured statements; CLI excluded |
| Ruff | Passed |
| Dependency audit | No known vulnerabilities reported for the resolved environment |
| Seed-7 synthetic demo | Completed; both HTML pages and mapping exports generated |
| Bicep compilation | Passed without signing in or deploying |
| Docker build and non-root execution | Passed |
| Python 3.11/3.12 permanent CI | Inspect the latest PR checks for the final source head |
| DeTT&CT YAML | Parsed and structurally tested against the official v1.2 example; external CLI not executed |
| Real-data effectiveness | Not validated |
| Azure live deployment | Not performed |

The exact reference environment is requirements-verified-py312-linux.txt. It is an environment snapshot,
not a hash-locked cross-platform specification. The project is installed separately.

The sample under examples/demo contains synthetic inspection outputs, including full-precision alerts.
Its manifest refers to the complete reproducible run, including files not copied into that sample bundle.
Synthetic metrics do not establish operational detection coverage. DeTT&CT scores remain draft -1/0
until an actual SOC deployment and telemetry are assessed; see docs/DETTCT_ES.md.

Remaining review: authorized real-data backtesting, campaign-level metrics and uncertainty, artifact
signing, hash-locked production dependencies, and live Azure student credit and deployment validation.
