# EAGLE-X v3.3 – Operational image
FROM python:3.11-slim as builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libssl-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

RUN useradd -m -s /bin/bash -u 1000 eaglex && \
    mkdir -p /var/log/eagle-x /app/data && \
    chown -R eaglex:eaglex /app /var/log/eagle-x

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY eaglex_v33.py api_server.py dashboard.html LICENSE signature.json \
     one-pager-technical.md compliance-report.md ./
COPY core/ core/

RUN chown -R eaglex:eaglex /app
USER eaglex

ENV EAGLE_MODE=production \
    EAGLE_VERSION=3.3 \
    EAGLE_SEAL=310-70-94 \
    LOG_LEVEL=INFO \
    EAGLE_LOG_DIR=/var/log/eagle-x \
    EAGLE_DATA_DIR=/app/data \
    EAGLE_API_TOKEN=eagle-x-dev-token-change-me

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health')" || exit 1

EXPOSE 8080
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8080"]
