# syntax=docker/dockerfile:1
# EAGLE-X v3.3 – image with optional prebuilt liboqs (ML-KEM / ML-DSA)

ARG ENABLE_PQC=1

# ── Stage 1: build liboqs + Python deps ───────────────────────────────────────
FROM python:3.11-slim AS builder
ARG ENABLE_PQC=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git libssl-dev libffi-dev python3-dev \
    ca-certificates wget \
    && rm -rf /var/lib/apt/lists/*

# Build liboqs from source when ENABLE_PQC=1 (pinned to match liboqs-python)
RUN if [ "$ENABLE_PQC" = "1" ]; then \
      git clone --depth 1 --branch 0.16.0 https://github.com/open-quantum-safe/liboqs.git && \
      cmake -S liboqs -B liboqs/build -GNinja \
        -DCMAKE_INSTALL_PREFIX=/usr/local \
        -DBUILD_SHARED_LIBS=ON \
        -DOQS_USE_OPENSSL=ON \
        -DOQS_BUILD_ONLY_LIB=ON && \
      cmake --build liboqs/build --parallel && \
      cmake --install liboqs/build && \
      ldconfig; \
    fi

WORKDIR /app
COPY requirements.txt requirements-optional.txt ./

ENV LD_LIBRARY_PATH=/usr/local/lib
ENV OQS_INSTALL_PATH=/usr/local

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    if [ "$ENABLE_PQC" = "1" ]; then \
      pip install --no-cache-dir "liboqs-python==0.16.0" "scapy>=2.5.0" || \
      pip install --no-cache-dir -r requirements-optional.txt || true; \
    fi

RUN if [ "$ENABLE_PQC" = "1" ]; then \
      python -c "import oqs; print('oqs OK', list(oqs.get_enabled_kem_mechanisms())[:5])" \
      || echo "oqs import deferred to runtime"; \
    fi

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime
ARG ENABLE_PQC=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/* && \
    useradd -m -s /bin/bash -u 1000 eaglex && \
    mkdir -p /var/log/eagle-x /app/data && \
    chown -R eaglex:eaglex /app /var/log/eagle-x

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/local/lib /usr/local/lib
COPY --from=builder /usr/local/include /usr/local/include

RUN echo "/usr/local/lib" > /etc/ld.so.conf.d/local.conf && ldconfig || true

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
    EAGLE_API_TOKEN=eagle-x-dev-token-change-me \
    LD_LIBRARY_PATH=/usr/local/lib \
    ENABLE_PQC=${ENABLE_PQC}

HEALTHCHECK --interval=30s --timeout=10s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health')" || exit 1

EXPOSE 8080
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8080"]
