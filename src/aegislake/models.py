"""Rule, novelty, and supervised baselines with validation-only selection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from aegislake.attack import describe_mapping
from aegislake.features import FEATURES


def rule_score(frame: pd.DataFrame) -> np.ndarray:
    spray = np.clip((frame["source_user_fanout"].to_numpy() - 3) / 12, 0, 1)
    failure = frame["fail_rate"].to_numpy()
    lateral = np.clip((frame["destinations"].to_numpy() - 2) / 8, 0, 1)
    volume = np.clip((frame["events"].to_numpy() - 3) / 15, 0, 1)
    return np.clip(
        0.4 * spray * failure + 0.3 * lateral + 0.15 * volume
        + 0.1 * frame["no_mfa_rate"].to_numpy() + 0.05 * frame["off_hours"].to_numpy(), 0, 1
    )


@dataclass
class Models:
    isolation: IsolationForest
    reference: np.ndarray
    logistic: object | None
    seed: int

    @classmethod
    def fit(cls, train: pd.DataFrame, seed: int = 42) -> Models:
        # Known-clean training where ground truth is available; otherwise contamination is unknown.
        clean = train.loc[train["label"].eq(0)]
        if len(clean) < 20:
            clean = train
        isolation = IsolationForest(n_estimators=200, max_samples=256, random_state=seed, n_jobs=1)
        isolation.fit(clean[FEATURES])
        reference = np.sort(-isolation.score_samples(clean[FEATURES]))
        labeled = train.loc[train["label"].notna()]
        logistic = None
        if labeled["label"].nunique() == 2:
            logistic = make_pipeline(
                StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000, random_state=seed)
            )
            logistic.fit(labeled[FEATURES], labeled["label"].astype(int))
        return cls(isolation, reference, logistic, seed)

    def score(self, frame: pd.DataFrame) -> dict[str, np.ndarray]:
        raw = -self.isolation.score_samples(frame[FEATURES])
        anomaly = np.searchsorted(self.reference, raw, side="right") / len(self.reference)
        rules = rule_score(frame)
        scores = {"rules": rules, "isolation_forest": anomaly, "hybrid": 0.6 * anomaly + 0.4 * rules}
        if self.logistic is not None:
            # Class-balanced probabilities are ranking scores, not calibrated incident probabilities.
            scores["logistic_regression"] = self.logistic.predict_proba(frame[FEATURES])[:, 1]
        return scores


def explain(row: pd.Series) -> dict:
    reasons = []
    techniques = []
    if row["source_user_fanout"] >= 8 and row["fail_rate"] >= 0.5:
        reasons.append("Shared source attempted many identities with frequent failures")
        techniques.append("T1110.003")
    if row["destinations"] >= 4:
        reasons.append("Identity accessed several destinations within one closed window")
        techniques.append("T1078")
    if row["new_destination_rate"] > 0:
        reasons.append("Some destinations were absent from the fixed training reference")
    if row["no_mfa_rate"] > 0.2:
        reasons.append("MFA absent from a material fraction of events")
    if row["off_hours"] > 0:
        reasons.append("Activity outside the demo's UTC business-hour convention")
    if not reasons:
        reasons.append("Statistical anomaly; no named rule matched")
    return {
        "reasons": reasons,
        "attack_hypotheses": sorted(set(techniques)), "attack_mapping": describe_mapping(techniques),
        "next_steps": [
            "Validate activity with the identity owner and approved change records",
            "Correlate endpoint and identity telemetry before escalation",
        ],
        "action": "human_review",
    }
