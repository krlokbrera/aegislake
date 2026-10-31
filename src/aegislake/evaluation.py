"""Metrics at operational capacity, with no use of test labels for selection."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_fscore_support, roc_auc_score


def select_threshold(frame: pd.DataFrame, scores: np.ndarray, capacity: int) -> float:
    if capacity < 1:
        raise ValueError("capacity must be positive")
    if frame["label"].isna().any() or frame["label"].nunique() < 2:
        raise ValueError("validation needs both labeled classes; no silent threshold calibration")
    if len(scores) != len(frame) or not np.isfinite(scores).all():
        raise ValueError("invalid score array")
    y = frame["label"].to_numpy(dtype=int)
    candidates = np.unique(np.quantile(scores, np.linspace(0, 1, 101)))
    candidates = np.append(candidates, np.nextafter(float(np.max(scores)), np.inf))
    best = (-1.0, -1.0, -1.0)
    chosen = float(candidates[-1])
    for threshold in candidates:
        # Calibrate the actual queue policy, including its stable daily top-k cap.
        predicted = queue_mask(frame, scores, float(threshold), capacity)
        precision, _, f1, _ = precision_recall_fscore_support(y, predicted, average="binary", zero_division=0)
        objective = (float(f1), float(precision), float(threshold))
        if objective > best:
            chosen, best = float(threshold), objective
    return chosen


def queue_mask(frame: pd.DataFrame, scores: np.ndarray, threshold: float, capacity: int) -> np.ndarray:
    if capacity < 1:
        raise ValueError("capacity must be positive")
    order = frame[["window_start", "user"]].reset_index(drop=True).copy()
    order["position"] = np.arange(len(order))
    order["score"] = scores
    order["day"] = order["window_start"].dt.strftime("%Y-%m-%d")
    eligible = order.loc[order["score"] >= threshold].sort_values(
        ["day", "score", "window_start", "user"], ascending=[True, False, True, True], kind="stable"
    )
    selected = eligible.groupby("day", sort=True).head(capacity)["position"].to_numpy(dtype=int)
    result = np.zeros(len(frame), dtype=bool)
    result[selected] = True
    return result


def metrics(frame: pd.DataFrame, scores: np.ndarray, threshold: float, capacity: int) -> dict:
    if frame["label"].isna().any():
        raise ValueError("evaluation requires complete ground truth")
    y = frame["label"].to_numpy(dtype=int)
    predicted = queue_mask(frame, scores, threshold, capacity)
    precision, recall, f1, _ = precision_recall_fscore_support(y, predicted, average="binary", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    days = frame["window_start"].dt.strftime("%Y-%m-%d")
    daily = pd.Series(predicted, index=frame.index).groupby(days).sum()
    positives = int(y.sum())
    negatives = int(len(y) - positives)
    return {
        "windows": len(y), "positive_windows": positives, "prevalence": float(y.mean()),
        "average_precision": float(average_precision_score(y, scores)) if positives else None,
        "roc_auc": float(roc_auc_score(y, scores)) if positives and negatives else None,
        "precision": float(precision), "recall": float(recall), "f1": float(f1),
        "false_positives_per_1000_benign": float(1000 * fp / negatives) if negatives else None,
        "alerts": int(predicted.sum()), "daily_alerts_mean": float(daily.mean()),
        "daily_alerts_max": int(daily.max()), "capacity_per_day": capacity,
        "threshold": float(threshold),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def population_stability_index(reference: np.ndarray, current: np.ndarray) -> float:
    # Diagnostic heuristic, not a significance test; fixed deciles learned from train.
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, 11)))
    edges = np.unique(np.concatenate(([-np.inf], edges[1:-1], [np.inf])))
    if len(edges) < 3:
        # Constant reference needs a dedicated deviation diagnostic.
        return float(np.mean(np.abs(current - reference[0]) > 1e-9))
    expected = np.histogram(reference, bins=edges)[0] / len(reference)
    actual = np.histogram(current, bins=edges)[0] / len(current)
    expected, actual = np.clip(expected, 1e-6, 1), np.clip(actual, 1e-6, 1)
    return float(np.sum((actual - expected) * np.log(actual / expected)))
