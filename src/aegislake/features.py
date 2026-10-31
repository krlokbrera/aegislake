"""Closed 15-minute windows; all historical novelty comes from train only."""

from __future__ import annotations

from datetime import timedelta

import duckdb
import numpy as np
import pandas as pd

FEATURES = [
    "events", "fail_rate", "destinations", "sources", "countries",
    "no_mfa_rate", "mfa_missing_rate", "source_user_fanout", "new_destination_rate", "off_hours",
]


def build_features(events: pd.DataFrame, train_before: pd.Timestamp) -> pd.DataFrame:
    history = events.loc[events["timestamp"] < train_before, ["user", "destination"]].drop_duplicates()
    if history.empty:
        raise ValueError("training history is empty")
    # Training-derived fixed reference, never fitted on validation/test.
    enriched = events.merge(history.assign(known_pair=1), on=["user", "destination"], how="left")
    enriched["is_new_destination"] = enriched["known_pair"].isna().astype(int)
    connection = duckdb.connect()
    try:
        connection.execute("SET TimeZone='UTC'")
        connection.register("events", enriched)
        # Transfer through Arrow to avoid DuckDB's legacy pandas conversion path.
        frame = connection.sql("""
            WITH base AS (
                SELECT *, time_bucket(INTERVAL '15 minutes', timestamp) AS window_start
                FROM events
            ), source_stats AS (
                SELECT window_start, source, count(DISTINCT "user") AS source_user_fanout
                FROM base GROUP BY window_start, source
            )
            SELECT b.window_start, b."user",
                b.window_start + INTERVAL '15 minutes' AS window_end,
                count(*)::DOUBLE AS events,
                avg(CASE WHEN success THEN 0.0 ELSE 1.0 END) AS fail_rate,
                count(DISTINCT destination)::DOUBLE AS destinations,
                count(DISTINCT b.source)::DOUBLE AS sources,
                count(DISTINCT country)::DOUBLE AS countries,
                coalesce(avg(CASE WHEN mfa = TRUE THEN 0.0 WHEN mfa = FALSE THEN 1.0 ELSE NULL END), 0.0)
                    AS no_mfa_rate,
                avg(CASE WHEN mfa IS NULL THEN 1.0 ELSE 0.0 END) AS mfa_missing_rate,
                max(s.source_user_fanout)::DOUBLE AS source_user_fanout,
                avg(is_new_destination)::DOUBLE AS new_destination_rate,
                CASE WHEN hour(b.window_start) < 7 OR hour(b.window_start) >= 20
                     THEN 1.0 ELSE 0.0 END AS off_hours,
                CASE WHEN count(label) = count(*) THEN max(label) ELSE NULL END AS label
            FROM base b JOIN source_stats s
                ON b.window_start = s.window_start AND b.source = s.source
            GROUP BY b.window_start, b."user"
            ORDER BY b.window_start, b."user"
        """).to_arrow_table().to_pandas()
    finally:
        connection.close()
    frame[FEATURES] = frame[FEATURES].astype("float64")
    for name in ("window_start", "window_end"):
        frame[name] = pd.to_datetime(frame[name], utc=True)
    if not np.isfinite(frame[FEATURES].to_numpy(dtype=float)).all():
        raise ValueError("non-finite feature values")
    return frame


def temporal_partitions(events: pd.DataFrame, train_days: int, validation_days: int):
    if train_days < 2 or validation_days < 1:
        raise ValueError("train_days >= 2 and validation_days >= 1 are required")
    origin = events["timestamp"].min().to_pydatetime().replace(hour=0, minute=0, second=0, microsecond=0)
    train_end = pd.Timestamp(origin + timedelta(days=train_days))
    validation_end = pd.Timestamp(origin + timedelta(days=train_days + validation_days))
    frame = build_features(events, train_end)
    # Align split to whole UTC days, so an aggregate never spans a split.
    train = frame[frame["window_end"] <= train_end].copy()
    validation = frame[(frame["window_start"] >= train_end) & (frame["window_end"] <= validation_end)].copy()
    test = frame[frame["window_start"] >= validation_end].copy()
    if any(part.empty for part in (train, validation, test)):
        raise ValueError("train, validation and test must all contain complete windows")
    return train, validation, test
