-- Run against a completed synthetic run; paths are examples relative to its directory.
-- Grain: one identity per closed 15-minute window, not one incident.
SELECT date_trunc('day', window_start) AS event_day,
       count(*) AS windows,
       sum(CASE WHEN fail_rate >= 0.5 THEN 1 ELSE 0 END) AS failure_heavy_windows,
       avg(mfa_missing_rate) AS average_missing_mfa,
       max(source_user_fanout) AS max_source_fanout
FROM read_parquet('gold/test_features.parquet')
GROUP BY event_day
ORDER BY event_day;

-- Daily investigation capacity is a batch allocation, not a streaming throttler.
SELECT substring(window_start, 1, 10) AS event_day, count(*) AS queued_alerts
FROM read_json_auto('gold/alerts.json')
GROUP BY event_day
ORDER BY event_day;
