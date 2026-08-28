# EAGLE-X v3.3 – Operational image (optional PQC build tools)
FROM python:3.11-slim as builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git libssl-dev libffi-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-optional.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    (pip install --no-cache-dir -r requirements-optional.txt || echo "optional deps skipped")

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 ca-certificates \
    && rm -rf /var/lib/apt/lists/* && \
    useradd -m -s /bin/bash -u 1000 eaglex && \
    mkdir -p /var/log/eagle-x /app/data && \
    chown -R eaglex:eaglex /app /var/log/eagle-x

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
# liboqs shared libs may land under site-packages or /usr/local/lib
COPY --from=builder /usr/local/lib /usr/local/lib

COPY eaglex_v33.py api_server.py dashboard.html LICENSE signature.json \
     one-pager-technical.md compliance-report.md ./
COPY core/ core/

RUN ldconfig 2>/dev/null || true && chown -R eaglex:eaglex /app
USER eaglex

ENV EAGLE_MODE=production \
    EAGLE_VERSION=3.3 \
    EAGLE_SEAL=310-70-94 \
    LOG_LEVEL=INFO \
    EAGLE_LOG_DIR=/var/log/eagle-x \
    EAGLE_DATA_DIR=/app/data \
    EAGLE_API_TOKEN=eagle-x-dev-token-change-me \
    LD_LIBRARY_PATH=/usr/local/lib

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health')" || exit 1

EXPOSE 8080
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8080"]
