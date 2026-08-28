#!/usr/bin/env bash
# Deploy EAGLE-X with Let's Encrypt TLS + PQC image
set -euo pipefail

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${EAGLE_DOMAIN:?Set EAGLE_DOMAIN (public hostname)}"
: "${CADDY_EMAIL:?Set CADDY_EMAIL for Let's Encrypt}"
: "${EAGLE_API_TOKEN:?Set EAGLE_API_TOKEN}"

if [[ "$EAGLE_DOMAIN" == "localhost" ]]; then
  echo "ERROR: EAGLE_DOMAIN=localhost cannot use public Let's Encrypt."
  echo "Use docker compose up for local TLS, or set a real domain."
  exit 1
fi

if [[ "$EAGLE_API_TOKEN" == "eagle-x-dev-token-change-me" || "$EAGLE_API_TOKEN" == "change-me-to-a-long-random-secret" ]]; then
  echo "ERROR: Set a strong unique EAGLE_API_TOKEN before production deploy."
  exit 1
fi

echo "==> Building image with prebuilt liboqs (ENABLE_PQC=${ENABLE_PQC:-1})"
echo "==> Domain: $EAGLE_DOMAIN"

docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

echo "==> Waiting for health..."
sleep 5
curl -fsS "https://${EAGLE_DOMAIN}/api/health" || curl -fsSk "https://${EAGLE_DOMAIN}/api/health" || true

echo "==> Status"
curl -fsS "https://${EAGLE_DOMAIN}/api/status" | head -c 500 || true
echo
echo "Done. Dashboard: https://${EAGLE_DOMAIN}/"
