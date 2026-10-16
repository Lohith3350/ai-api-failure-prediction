# Architecture and integration contracts

## Shared telemetry contract
All telemetry producers should emit records with these fields where available:
- `timestamp` (ISO-8601 string)
- `service_name` (string)
- `response_time_ms` (number)
- `request_count` (integer)
- `error_rate` (0–1 fraction; use the same convention everywhere)
- `http_5xx_count` (integer)
- `timeout_count` (integer)
- `cpu_usage_pct` (0–100 or null)
- `memory_usage_pct` (0–100 or null)
- `dependency_latency_ms` (number or null)

## Prediction contract
Prediction service should return:
- `service_name`
- `failure_probability` (0–1)
- `risk_level` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- `reasons` (list of human-readable evidence strings)

## Integration principles
- Keep model inference separate from API route handlers.
- Use synthetic data first, then evaluate on a separate test set.
- Prediction means risk within a defined future horizon; document that horizon.
- Do not use random train/test row splits for time-series records if they leak future information.
- Keep automatic infrastructure changes simulated until thoroughly tested.
