# Model card

## Intended use

Offline research and portfolio demonstration of identity threat ranking, with analyst review. Model outputs identify user/time windows for investigation; they do not establish that an identity is compromised.

## Prediction unit and features

The unit is one identity in a closed 15-minute UTC window.

| Feature | Meaning | Limitation |
| --- | --- | --- |
| events | Number of events | Legitimate batch jobs can be busy |
| fail_rate | Fraction of failed events | Stale passwords and outages can resemble attacks |
| destinations | Distinct target resources | Administrator work can have broad reach |
| sources | Distinct sources | VPNs and distributed clients affect this count |
| countries | Distinct country values | Geolocation is coarse and may be unknown |
| no_mfa_rate | Observed MFA absence among known MFA values | Unknown MFA is handled separately |
| mfa_missing_rate | Fraction with unavailable MFA evidence | Missingness can reflect collection, not risk |
| source_user_fanout | Maximum identities using one source in the window | Shared NAT and proxies create confounding |
| new_destination_rate | Fraction of destinations absent from train reference | Fixed reference grows stale |
| off_hours | Window outside the demo UTC convention | Not an employee's local schedule |

Identifiers, labels and scenario names are excluded through an explicit feature allowlist. Labels are allowed for training and evaluation purposes, never as input features.

## Candidates

| Candidate | Training | Score interpretation |
| --- | --- | --- |
| Rules | Fixed weights in code | Handcrafted heuristic score |
| Isolation Forest | Known-benign train windows when available, otherwise all train windows | Empirical anomaly percentile against the train reference |
| Logistic regression | Labeled train windows; standardized inputs; balanced class weights | Ranking score from an uncalibrated classifier |
| Hybrid | Fixed 60% anomaly percentile and 40% rule score | Composite ranking heuristic |

The anomaly detector's empirical percentile and the classifier output are not probabilities of compromise. The balanced classifier in particular changes effective class priors.

## Temporal evaluation

Defaults: days 1–18 train, days 19–24 validation, days 25–30 test. Boundaries derive from the first UTC day of input. A run fails when any partition is empty.

Preprocessing and the anomaly reference are fitted only on train. Thresholds are chosen from validation score quantiles, with a daily capacity constraint. Each candidate's validation F1 is evaluated on its capacity-limited queue. The champion is selected by validation F1, then precision, then a deterministic model-name tie-break. Test scores are reported after selection; they do not select the champion.

This is one temporal holdout, not repeated cross-validation or an unbiased estimate across organizations. Campaigns from the same simulator recur across periods. Event-level independence cannot be assumed, and window-level recall is not campaign recall.

## Capacity policy

Every validation threshold is evaluated with the same stable daily top-k queue policy used at test time. Calibration optimizes validation F1 on that final queue, rather than rejecting useful score ties because their uncapped volume exceeds capacity. A dedicated regression test covers this case.

The operating-point policy was revised after inspecting development results with seed 42. The bundled example uses seed 7, fixed before inspecting its outputs. Both are illustrative simulator experiments, not an independent real-world benchmark.

Test and future batches also apply a hard daily top-k cap among eligible windows. The policy is retrospective within a completed daily batch. It is not a real-time rate limiter, and a high volume of noisy windows may push true attacks out of the queue.

## Metrics

Average precision summarizes ranking under class imbalance. ROC AUC is secondary. Precision, recall, F1, confusion matrix, false positives per thousand benign windows, and actual queue volume describe the final capacity-limited selection.

Undefined ROC AUC is reported as null for one-class test data. Average precision is null when no positive labels are present. Validation requires both labeled classes so model selection cannot silently use meaningless scores.

Confidence intervals and campaign-level metrics are planned. Treat all displayed values as descriptive for the specific dataset and period.

## Explanation mechanism

Alert text is generated from deterministic feature conditions and fixed templates. ATT&CK identifiers are hypotheses attached to observable patterns. They are not verified attributions or proof of a technique. These templates are not SHAP values, causal explanations, or generative model outputs.

## Monitoring

The report compares train and test marginal feature distributions using fixed train-derived bins. Constant features use a separate changed-fraction diagnostic under the same output field. These are exploratory diagnostics; no universal PSI threshold is used and no automatic retraining occurs.

A deployment should also monitor source freshness, missing fields, duplicate/conflict rates, label adjudication delays and queue saturation. Joint drift, adversarial adaptation and feedback bias remain unmeasured.

## Misuse and deployment exclusions

Do not use the demo to automatically disable accounts, score employees for employment decisions, identify insiders by personal traits, or claim production detection coverage. Entra scoring from a synthetic reference requires a deliberate domain-shift override and remains experimental.

## Reproduction and persistence

Each run records input and artifact hashes, package versions, seed and split configuration. Future scoring reconstructs the model from training features with matching dependency versions. No pickle or joblib model artifact is loaded. Run hashes are integrity references, not signed provenance.

## Acceptance gates

Before a production pilot: representative authorized data, independent label review, time-based backtests, realistic shared-IP/VPN behavior, latency and late-event tests, analyst workload evaluation, domain-specific thresholds, access review, and a rollback plan.

These gates are evaluation requirements, not claims that the reference implementation already satisfies them.
