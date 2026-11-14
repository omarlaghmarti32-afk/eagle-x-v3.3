# EAGLE-X v3.3

Defensive cybersecurity monitoring service with explainable anomaly detection, auditable response simulation, and optional post-quantum library integration.

**https://github.com/omarlaghmarti32-afk/eagle-x-v3.3** · **v3.3.2**

## Quick start

```bash
git clone https://github.com/omarlaghmarti32-afk/eagle-x-v3.3.git
cd eagle-x-v3.3
pip install -r requirements.txt

export EAGLE_API_TOKEN=$(openssl rand -hex 24)
export EAGLE_REQUIRE_STRONG_TOKEN=1
export EAGLE_LIVE_MONITOR=1

uvicorn api_server:app --host 0.0.0.0 --port 8080
```

Open http://127.0.0.1:8080

## Docker

```bash
cp .env.example .env
# edit .env — set a strong EAGLE_API_TOKEN
docker compose up -d --build
```

## Security (v3.3.2)

- Constant-time Bearer compare (`secrets.compare_digest`)
- Strong-token enforcement: `EAGLE_REQUIRE_STRONG_TOKEN=1` (default in Docker)
- Configurable CORS: `EAGLE_CORS_ORIGINS`
- Security headers (CSP, X-Frame-Options, nosniff, HSTS on HTTPS)
- Rate limiting on mutating `/api/*` routes
- Optional read-API lock: `EAGLE_PROTECT_READ_APIS=1`
- SSRF guard on health-monitor webhooks
- Docker: **no baked-in API token**; non-root user; `no-new-privileges`; `REQUIRE_STRONG_TOKEN=1`
- Compose requires `EAGLE_API_TOKEN` from `.env` (fails if missing)

See [SECURITY.md](SECURITY.md) for reporting and operator checklist.

## API (selected)

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/health` | public |
| GET | `/api/ready` | public |
| GET | `/api/status` | optional (`PROTECT_READ_APIS`) |
| GET | `/api/github/overview` | Bearer (`EAGLE_API_TOKEN`, always required) |
| POST | `/api/detect` | Bearer |
| POST | `/api/heal` | Bearer |
| GET | `/api/blocklist` | Bearer |
| WebSocket | `/ws` | token message first |

The dashboard uses `/ws` for authenticated live samples and threat events, with
short-interval REST refresh as a fallback. Send `{"token":"<EAGLE_API_TOKEN>"}`
as the first WebSocket message; use `wss://` behind TLS.

## GitHub Security Command Center

The Arabic dashboard includes a read-only GitHub view for repository metadata,
recent Actions runs, deployment statuses, Dependabot alerts, and code-scanning
alerts. It ranks failures and findings and gives a short Arabic explanation and
next action. The API endpoint is `GET /api/github/overview` and always requires
the EAGLE-X Bearer token, including when read APIs are otherwise public.

Set `EAGLE_GITHUB_REPO=owner/repository` on the server. Public repository and
workflow/deployment data can be read without a GitHub token. To see vulnerability
alerts, create a fine-grained GitHub token with read-only access to **Actions**,
**Deployments**, **Dependabot alerts**, and **Code scanning alerts**, then set it
as `EAGLE_GITHUB_TOKEN` in the server environment or local `.env` file. Docker
Compose passes it only to the API container. Never put this GitHub token in the
browser or commit it to the repository. When alerts are inaccessible, the panel
marks vulnerability coverage as incomplete instead of claiming there are zero
vulnerabilities. Re-deploy or restart the service after changing environment
variables.

The repository must also have Dependabot alerts and code scanning enabled under
GitHub **Settings → Code security and analysis**; code scanning additionally
needs an active scanning workflow or tool. If a feature is disabled, the panel
identifies it instead of treating it as a clean scan.

For a local run, copy `.env.example` to `.env`, add the optional GitHub token,
and run `docker compose up -d --build`. In the dashboard, enter the
`EAGLE_API_TOKEN` in its existing token field; the GitHub token is never entered
there.

## Decentralized deployment templates

- [`deploy.yml`](deploy.yml): Akash SDL for the backend.
- [`fleek.json`](fleek.json): Fleek/IPFS static dashboard template.
- [`spheron.json`](spheron.json): Spheron Docker alternative.
- [`DEPLOYMENT.md`](DEPLOYMENT.md): operator steps and secret-handling rules.
- [`ARCHITECTURE.md`](ARCHITECTURE.md): components, trust boundaries, and scaling notes.

These files contain placeholders only. No wallet, provider lease, API token, or
paid deployment is created by CI.

## Tests

```bash
EAGLE_REQUIRE_STRONG_TOKEN=0 EAGLE_LIVE_MONITOR=0 pytest -q
```

## License

See LICENSE.
