import numpy as np
import pandas as pd
import pytest

from aegislake.evaluation import metrics, population_stability_index, queue_mask, select_threshold


def data():
    return pd.DataFrame({
        "window_start": pd.to_datetime(["2026-01-01T10:00Z"] * 4 + ["2026-01-02T10:00Z"] * 4),
        "user": ["a", "b", "c", "d"] * 2, "label": [0, 1, 0, 0, 0, 1, 0, 0],
    })


def test_threshold_respects_validation_capacity():
    frame = data()
    scores = np.array([0.1, 0.95, 0.3, 0.2, 0.2, 0.9, 0.4, 0.1])
    threshold = select_threshold(frame, scores, 1)
    result = metrics(frame, scores, threshold, 1)
    assert result["precision"] == 1
    assert result["recall"] == 1
    assert result["daily_alerts_max"] == 1


def test_test_volume_spike_still_capped_with_stable_ties():
    frame = data()
    selected = queue_mask(frame, np.ones(8), 0.5, 1)
    assert selected.tolist() == [True, False, False, False, True, False, False, False]
    assert selected.sum() == 2


def test_single_class_metrics_and_validation_guard():
    frame = data().assign(label=0)
    result = metrics(frame, np.arange(8) / 8, 0.5, 2)
    assert result["roc_auc"] is None
    assert result["average_precision"] is None
    with pytest.raises(ValueError, match="both labeled classes"):
        select_threshold(frame, np.zeros(8), 2)


def test_missing_labels_and_bad_capacity_rejected():
    frame = data()
    frame.loc[0, "label"] = np.nan
    with pytest.raises(ValueError):
        select_threshold(frame, np.zeros(8), 2)
    with pytest.raises(ValueError):
        queue_mask(data(), np.zeros(8), 0.5, 0)


def test_drift_identical_reference_is_zero():
    values = np.arange(100, dtype=float)
    assert population_stability_index(values, values) == pytest.approx(0)
    assert population_stability_index(np.zeros(100), np.ones(100)) == 1
