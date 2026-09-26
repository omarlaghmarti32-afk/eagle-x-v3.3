# EAGLE-X v3.3 Architecture

EAGLE-X is a **defensive host-monitoring demonstration service**. It detects anomalous host telemetry, records an auditable event, and can run a policy-controlled simulated response. It is not an offensive scanner and does not claim cryptographic invulnerability or a measured detection accuracy.

## Components

```text
Browser dashboard
   | HTTPS REST + authenticated WebSocket (/ws)
   v
FastAPI API (api_server.py)
   |-- token authentication, CORS, headers, rate limiting
   |-- health/readiness endpoints
   |-- request validation and audit events
   |-- live update fan-out (single process)
   +--> AIThreatDetector  ---> analysis result (demo model)
   +--> NetworkMonitor    ---> psutil host feature vector
   +--> PQCManager        ---> approved-library mode or explicit simulation
   +--> SelfHealingEngine ---> policy-controlled defensive simulation
   +--> ThreatDB          ---> SQLite threats, metrics, blocklist, audit

Optional health-monitor sidecar -> /api/health/deep -> safe webhook
```

## Runtime flow

1. `NetworkMonitor` samples local host metrics; packet capture is disabled by default.
2. The detector classifies the feature vector and returns an explainable result.
3. Detected events are stored in SQLite with timestamp, source, severity, and sealed metadata.
4. The API broadcasts non-sensitive sample summaries and threat events to authenticated WebSocket clients.
5. Self-healing remains a simulation/policy layer. Any future real response must be separately reviewed, allow-listed, rate-limited, and auditable.

## Trust boundaries

- **Client to API:** bearer token for REST mutations and an explicit first WebSocket message. TLS must terminate at Caddy or the deployment provider.
- **API to host:** psutil reads local telemetry. Optional packet capture requires explicit operator enablement and elevated host capabilities; it is off in the default Compose path.
- **API to external webhook:** health monitor rejects localhost, private, link-local, metadata, and internal targets by default.
- **Persistence:** SQLite and audit logs are mounted volumes. Back them up and restrict filesystem permissions.

## Scaling notes

The WebSocket manager is intentionally in-process. Run one API replica unless a shared broker is added. For multiple replicas, use a managed pub/sub channel and move rate-limit state out of process. SQLite is suitable for a single-node demo/operations console; production deployments should use a managed database after a schema and migration review.

## Security properties

- Strong-token startup policy in production.
- Constant-time token comparison.
- Explicit CORS and security headers.
- Mutating-route rate limiting and optional read-route protection.
- Pydantic request validation and bounded response sizes.
- Structured audit events for startup, health, detections, and simulated healing.

See [SECURITY.md](SECURITY.md) and [DEPLOYMENT.md](DEPLOYMENT.md) for operator controls and deployment procedures.
