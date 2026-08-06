# ═══════════════════════════════════════════════════════════════════════════════
# EAGLE-X v3.3 – Production Docker Image (Dashboard & API Enabled)
# ═══════════════════════════════════════════════════════════════════════════════
# Seal: 310-70-94
# License: Commercial - All Rights Reserved © 2025
# ═══════════════════════════════════════════════════════════════════════════════

FROM python:3.11-slim as builder

LABEL com.eaglex.version="3.3"
LABEL com.eaglex.seal="310-70-94"
LABEL com.eaglex.signed_by="Noran Ultimate Systems"
LABEL com.eaglex.license="Commercial - All Rights Reserved"
LABEL com.eaglex.description="Quantum-Resistant Cybersecurity Titan with Dashboard & API"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

RUN useradd -m -s /bin/bash -u 1000 eaglex && \
    mkdir -p /var/log/eagle-x && \
    chown -R eaglex:eaglex /app /var/log/eagle-x

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY eaglex_v33.py .
COPY api_server.py .
COPY dashboard.html .
COPY LICENSE .
COPY signature.json .
COPY one-pager-technical.md .
COPY compliance-report.md .
COPY core/ core/

RUN echo "EAGLE-X v3.3 | Seal: 310-70-94 | Built: $(date -u +'%Y-%m-%dT%H:%M:%SZ')" > signature.txt && \
    chown eaglex:eaglex signature.txt

USER eaglex

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; res = requests.get('http://localhost:8080/api/status'); exit(0 if res.status_code == 200 else 1)" || exit 1

EXPOSE 8080

ENV EAGLE_MODE=production \
    EAGLE_VERSION=3.3 \
    EAGLE_SEAL=310-70-94 \
    LOG_LEVEL=INFO

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8080"]
