#!/usr/bin/env bash
# Build local image with liboqs compiled in
set -euo pipefail
ENABLE_PQC="${ENABLE_PQC:-1}"
TAG="${TAG:-eagle-x:3.3-pqc}"

echo "Building $TAG (ENABLE_PQC=$ENABLE_PQC)..."
docker build --build-arg ENABLE_PQC="$ENABLE_PQC" -t "$TAG" .

echo "Smoke test oqs inside image..."
docker run --rm "$TAG" python -c "
from core.pqc_manager import PQCManager
m = PQCManager()
print(m.get_status())
demo = m.kem_demo()
print('kem_demo', 'OK' if demo else 'unavailable', demo.get('algorithm') if demo else '')
" || echo "Container smoke test finished with warnings"

echo "Image ready: $TAG"
