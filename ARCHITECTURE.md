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
   +--> Detection rules   ---> local metric thresholds, incident transitions
   +--> ThreatDB          ---> SQLite threats, metrics, telemetry events, assets, rules, incidents, audit
Local telemetry producers -> authenticated /api/telemetry/events -> validation -> rules -> SQLite

Optional GitHub read-only view (off by default; enabled only by operator)
Optional health-monitor sidecar -> /api/health/deep -> optional safe webhook
```

## Runtime flow

1. `NetworkMonitor` samples local host metrics; packet capture is disabled by default.
2. The detector classifies the feature vector and returns an explainable result.
3. Detected events are stored in SQLite with timestamp, source, severity, and sealed metadata.
   Operators can also maintain a local asset inventory and incident lifecycle in the same database;
   incidents may reference known assets without launching a scan or contacting an external service.
4. Enabled local detection rules compare sampled host metrics against operator-defined thresholds.
   A transition into a breach creates one asset-linked incident and an audit event; repeated samples
   do not create duplicates, while a clear-then-rebreach starts a new incident.
5. The API broadcasts non-sensitive sample summaries and threat events to authenticated WebSocket clients.
6. Self-healing remains a simulation/policy layer. Any future real response must be separately reviewed, allow-listed, rate-limited, and auditable.
7. Local producers may submit batches of up to 100 metric events. The API validates known metric names, stores the event locally, evaluates only global rules and rules linked to that event's asset, and broadcasts newly created incidents.

## Trust boundaries

- **Client to API:** bearer token for REST mutations and an explicit first WebSocket message. TLS must terminate at Caddy or the deployment provider.
- **Telemetry producer to API:** the event-ingestion endpoint requires the same bearer token, limits batch size, rejects unknown/non-finite metrics, and deduplicates retried events by source plus event ID. Submitted events and rule outcomes remain in local SQLite; the endpoint does not forward them to a third party.
- **API to host:** psutil reads local telemetry. Optional packet capture requires explicit operator enablement and elevated host capabilities; it is off in the default Compose path.
- **Default network behavior:** local host monitoring, AI and threshold detection, dashboard API, SQLite persistence, asset inventory, incident tracking, and audit work without an external SaaS account. The dashboard itself loads no CDN or third-party fonts. GitHub access is disabled unless `EAGLE_GITHUB_ENABLED=1`; the health webhook is unused unless explicitly configured.
- **Sensitive local records:** asset and incident API routes always require the EAGLE-X bearer token, independently of the optional read-route protection setting.
- **API to external webhook:** when configured, the health monitor rejects localhost, private, link-local, metadata, and internal targets by default.
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
