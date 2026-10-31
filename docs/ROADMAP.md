# Review roadmap

## Milestone 1: verified vertical slice

Acceptance: dependency resolution, Ruff, pytest, pip-audit, default demo, visual report review, Bicep compilation and Docker build all observed. Publish a reviewed exact dependency lock. No unobserved metrics in the README.

## Milestone 2: Azure for Students demonstration

Acceptance: active student offer and available balance verified; regional quota confirmed; what-if reviewed; dedicated resources deployed; anonymous report read denied; authorized read succeeds; optional job completes and exits.

## Milestone 3: independent validation

Acceptance: authorized representative data and adjudicated labels, explicit dataset terms, multiple temporal folds, campaign-level analysis, shared-IP/VPN tests and uncertainty estimates.

## Milestone 4: operational batch service

Acceptance: bounded inputs, late-arrival policy, source freshness metrics, retry-safe upload staging, independent artifact signing, safe model registry and multi-analyst ledger controls.

## Suggested PR boundaries

| PR | Scope | Review focus |
| --- | --- | --- |
| 1 | Core package, demo, tests, cards and research | Data correctness and honest evaluation |
| 2 | Azure infrastructure and deployment scripts | Offer, permissions, networking, cost and live verification |
| 3 | Real-data benchmark adapter | Data authorization, label joins and temporal validity |
| 4 | Operational hardening | Input bounds, artifact trust and failure recovery |

Every PR should state observed validation and remaining blockers. A PR is a review surface for concrete code; planned functionality belongs in issues rather than empty PRs.
