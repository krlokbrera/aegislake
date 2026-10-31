import warnings

import numpy as np
import pandas as pd

from aegislake.features import FEATURES, build_features
from aegislake.models import Models


def frame(rows):
    events = pd.DataFrame(rows)
    events["timestamp"] = pd.to_datetime(events["timestamp"], utc=True)
    if "scenario" not in events:
        events["scenario"] = "test"
    return events


def test_future_destination_does_not_leak_into_reference(event):
    events = frame([
        event,
        event | {"event_id": "e2", "timestamp": "2026-01-07T10:01:00Z", "destination": "future-only"},
    ])
    features = build_features(events, pd.Timestamp("2026-01-06T00:00:00Z"))
    assert features.iloc[0]["new_destination_rate"] == 0
    assert features.iloc[1]["new_destination_rate"] == 1
    changed = events.copy()
    changed.loc[1, "destination"] = "another-future-app"
    changed_features = build_features(changed, pd.Timestamp("2026-01-06T00:00:00Z"))
    np.testing.assert_allclose(features.iloc[[0]][FEATURES], changed_features.iloc[[0]][FEATURES])


def test_source_fanout_and_closed_windows(event):
    events = frame([
        event | {"user": "a", "event_id": "a", "success": False},
        event | {"user": "b", "event_id": "b", "success": False, "mfa": None},
        event | {"user": "c", "event_id": "c", "timestamp": "2026-01-05T10:16:00Z"},
    ])
    features = build_features(events, pd.Timestamp("2026-01-06T00:00:00Z"))
    first = features.loc[features["user"].eq("a")].iloc[0]
    second = features.loc[features["user"].eq("b")].iloc[0]
    third = features.loc[features["user"].eq("c")].iloc[0]
    assert first["source_user_fanout"] == 2
    assert second["mfa_missing_rate"] == 1
    assert second["no_mfa_rate"] == 0
    assert third["source_user_fanout"] == 1
    assert first["window_end"] == pd.Timestamp("2026-01-05T10:15:00Z")


def test_feature_allowlist_never_contains_target_or_identifiers():
    assert not set(FEATURES) & {"label", "scenario", "user", "source", "destination", "event_id", "timestamp"}


def test_arrow_transfer_preserves_utc_and_unknown_labels_without_warnings(event):
    events = frame([
        event | {"event_id": "history", "timestamp": "2026-01-04T10:00:00Z"},
        event | {"event_id": "future", "timestamp": "2026-01-05T07:16:00+01:00", "label": None, "mfa": None},
    ])
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = build_features(events, pd.Timestamp("2026-01-05T00:00:00Z"))
    future = result.loc[result["window_start"] == pd.Timestamp("2026-01-05T06:15:00Z")].iloc[0]
    assert future["window_end"] == pd.Timestamp("2026-01-05T06:30:00Z")
    assert str(result["window_start"].dt.tz) == "UTC"
    assert all(result[name].dtype == np.dtype("float64") for name in FEATURES)
    assert pd.isna(future["label"])
    assert future["mfa_missing_rate"] == 1
    assert future["no_mfa_rate"] == 0
    assert future["off_hours"] == 1


def test_off_hours_uses_utc_even_when_connection_starts_in_another_timezone(event, monkeypatch):
    import aegislake.features as module

    original_connect = module.duckdb.connect

    def non_utc_connection():
        connection = original_connect()
        connection.execute("SET TimeZone='Europe/Madrid'")
        return connection

    monkeypatch.setattr(module.duckdb, "connect", non_utc_connection)
    result = build_features(frame([event | {"timestamp": "2026-01-05T06:16:00Z"}]),
                            pd.Timestamp("2026-01-06T00:00:00Z"))
    assert result.iloc[0]["off_hours"] == 1
    assert result.iloc[0]["window_start"].isoformat() == "2026-01-05T06:15:00+00:00"


def test_models_fit_and_scores_are_bounded(completed_run):
    _, path = completed_run
    train = pd.read_parquet(path / "gold/train_features.parquet")
    test = pd.read_parquet(path / "gold/test_features.parquet")
    models = Models.fit(train, seed=123)
    for values in models.score(test).values():
        assert len(values) == len(test)
        assert np.isfinite(values).all()
        assert (values >= 0).all() and (values <= 1).all()
