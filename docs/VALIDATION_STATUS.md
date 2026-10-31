# Validation status and evidence ledger

Release 0.2.0 verified in an isolated Python 3.12 Linux environment.
Evidence: https://github.com/krlokbrera/aegislake/actions/runs/41227547021

| Check | Observed result |
| --- | --- |
| Regression, HTTP isolation and scoring tests | 74 passed |
| Python statement coverage | 90%; CLI excluded |
| Ruff | Passed |
| Dependency audit | No known vulnerabilities reported for the resolved environment |
| Fresh seed-7 example | Completed; native dashboard, Overview, MITRE and exports generated |
| Bicep compilation | Passed without deploying |
| Non-root Docker build and execution | Passed |
| Python 3.11/3.12 permanent CI | Inspect final-source PR checks |
| Browser validation and remaining visual checks | See FRONTEND_REVIEW_ES.md |
| Real SIEM connection / live Azure deployment | Not performed |

requirements-verified-py312-linux.txt records the resolved release environment. It is not a
hash-locked production specification. requirements-verified-py311-windows.txt records local QA.
The inspection bundle is synthetic and omits some files described by its complete-run manifest.
Alert counts and ranking scores do not establish operational detection coverage. DeTT&CT scores
remain an unassessed draft. See DASHBOARDS_ES.md and DETTCT_ES.md for scope and limits.
