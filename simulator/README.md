# API simulator — Kishor
Build a small service set (e.g. user, order, payment) and a load/failure simulator.

Suggested scenarios:
- Normal traffic
- Gradual latency increase
- Rising HTTP 5xx/timeouts
- Database/dependency slowdown

Output telemetry matching `backend/app/schemas.py::TelemetryRecord`.
