# Deployment Guide

This guide prepares deployment artifacts but does **not** create wallets, bids, DNS records, hosted sites, or paid resources. Supply secrets through each platform's secret manager; never commit `.env` or a token.

## 1. Local Docker Compose (recommended first validation)

```bash
cp .env.example .env
python3 -c 'import secrets; print("EAGLE_API_TOKEN=" + secrets.token_hex(24))'
# Put the generated value in .env, then:
docker compose config
docker compose up -d --build
curl -fsS http://127.0.0.1/api/ready
```

The API listens behind Caddy. Keep `EAGLE_CORS_ORIGINS` restricted to the dashboard origin and use `EAGLE_PROTECT_READ_APIS=1` for an internet-facing service.

## 2. Akash Network (backend)

`deploy.yml` is an SDL template. Before submitting it:

1. Publish a reviewed image to a registry accessible by the selected provider.
2. Replace the image tag if required and set resource/pricing values for the target market.
3. Inject `EAGLE_API_TOKEN` and `EAGLE_CORS_ORIGINS` through the deployment workflow or provider secret mechanism. Do not put literal values in SDL or shell history.
4. Validate with the Akash CLI, create a deployment, inspect the provider's lease, and verify `/api/ready` over TLS.
5. Configure persistent storage for `/app/data`; SQLite is single-node only.

The file is deliberately a template: provider selection, wallet signing, bids, and payments require the operator and are not performed by this repository.

## 3. Fleek/IPFS (frontend)

`fleek.json` describes a static publish of the dashboard assets. The dashboard must reach the backend through a public HTTPS API origin or a reverse proxy. IPFS content is public by default; **never place an API token in HTML, JavaScript, build logs, or IPFS-published files**.

Recommended flow:

1. Create a Fleek site manually and store its site ID in the platform configuration.
2. Configure the API origin as a public HTTPS URL with restricted CORS.
3. Publish only the static frontend and verify that WebSocket upgrades use `wss://`.
4. Pin the resulting CID and record it in change management.

## 4. Spheron alternative

`spheron.json` is a Docker deployment template for a single API replica with a health check and a persistent data mount. Map the `${...}` values to Spheron's secret/environment settings, choose a region/provider, and verify TLS, persistence, logs, and `/api/ready` before exposing the service.

## CI/CD

- `.github/workflows/ci.yml` runs tests on pushes and pull requests.
- `.github/workflows/docker-publish.yml` publishes only on version tags or manual dispatch and performs a health check.
- Deployment to decentralized providers is intentionally manual until provider credentials, image registry policy, and approval gates are defined.

## Operational checklist

- [ ] Strong random `EAGLE_API_TOKEN` stored in a secret manager.
- [ ] `EAGLE_REQUIRE_STRONG_TOKEN=1` and `EAGLE_PROTECT_READ_APIS=1`.
- [ ] Restricted CORS; TLS enabled; no direct public port exposure.
- [ ] Persistent data and audit-log backup tested.
- [ ] Provider network policy permits only required API traffic.
- [ ] Alerts tested without sending sensitive telemetry to third parties.
- [ ] Rollback image/tag and incident contact documented.
