# EAGLE-X v3.3

Quantum-Resistant Cybersecurity Titan — enterprise-grade security system with AI prediction, self-healing, and quantum resistance.

**https://github.com/omarlaghmarti32-afk/eagle-x-v3.3** · **v3.3.1**

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

## Security (v3.3.1)

- Constant-time Bearer compare (`secrets.compare_digest`)
- Strong-token enforcement: `EAGLE_REQUIRE_STRONG_TOKEN=1` (default in Docker)
- Configurable CORS: `EAGLE_CORS_ORIGINS`
- Security headers (CSP, X-Frame-Options, nosniff, HSTS on HTTPS)
- Rate limiting on mutating `/api/*` routes
- Optional read-API lock: `EAGLE_PROTECT_READ_APIS=1`
- Docker: **no baked-in API token**; non-root user; `REQUIRE_STRONG_TOKEN=1`

Set a real secret before production:

```bash
export EAGLE_API_TOKEN=$(openssl rand -hex 24)
```

## API (selected)

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/health` | public |
| GET | `/api/ready` | public |
| GET | `/api/status` | optional (`PROTECT_READ_APIS`) |
| POST | `/api/detect` | Bearer |
| POST | `/api/heal` | Bearer |
| GET | `/api/blocklist` | Bearer |

## Tests

```bash
EAGLE_REQUIRE_STRONG_TOKEN=0 EAGLE_LIVE_MONITOR=0 pytest -q
```

## License

See LICENSE.
