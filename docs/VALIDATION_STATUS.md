# Validation status and evidence ledger

Verified on 2026-10-31 in an isolated GitHub Actions Python 3.12 Linux environment.

Evidence: [https://github.com/krlokbrera/aegislake/actions/runs/41214818529](https://github.com/krlokbrera/aegislake/actions/runs/41214818529)

| Check | Observed result |
| --- | --- |
| Python regression and end-to-end tests | 31 passed |
| Coverage | 87% of measured statements; CLI excluded |
| Ruff | Passed |
| Dependency audit | No known vulnerabilities reported for the resolved environment |
| Default synthetic demo | Completed; report and manifest archived |
| Azure Bicep compilation | Passed without deployment |
| Docker build | Passed |
| Non-root container demo | Completed |
| Python 3.11/3.12 CI matrix | See the PR checks for the latest head |
| Real-data effectiveness | Not validated |
| Azure student credit and live deployment | Not verified; no Azure resources created |

A separate CI run initially identified vulnerable preinstalled setuptools in the Python 3.11 runner. CI now creates a virtual environment and upgrades packaging tools before installing and auditing project dependencies.

The exact Python 3.12 reference environment is stored in requirements-verified-py312-linux.txt. This is an environment snapshot, not a hash-locked cross-platform dependency specification. Original project code is installed separately.

The generated examples/demo report contains synthetic data only. Its scores describe the simulator, not real-world effectiveness. The manifest refers to full run artifacts retained by CI or reproducible locally.

Remaining review: authorized real-data backtesting, campaign-level metrics and uncertainty, a signed model/artifact registry, hash-locked production dependencies, and live Azure for Students access/cost verification.
