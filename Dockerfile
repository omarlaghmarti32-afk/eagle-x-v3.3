# ═══════════════════════════════════════════════════════════════════════════════
# EAGLE-X v3.3 – Production Docker Image
# ═══════════════════════════════════════════════════════════════════════════════
# Seal: 310-70-94
# License: Commercial - All Rights Reserved © 2025
# ═══════════════════════════════════════════════════════════════════════════════

FROM python:3.11-slim as builder

LABEL com.eaglex.version="3.3"
LABEL com.eaglex.seal="310-70-94"
LABEL com.eaglex.signed_by="Noran Ultimate Systems"
LABEL com.eaglex.license="Commercial - All Rights Reserved"
LABEL com.eaglex.description="Quantum-Resistant Cybersecurity Titan"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -s /bin/bash -u 1000 eaglex && \
    mkdir -p /var/log/eagle-x && \
    chown -R eaglex:eaglex /app /var/log/eagle-x

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY eaglex_v33.py .
COPY LICENSE .
COPY signature.json .
COPY one-pager-technical.md .
COPY compliance-report.md .

# Create signature file with build timestamp
RUN echo "EAGLE-X v3.3 | Seal: 310-70-94 | Built: $(date -u +'%Y-%m-%dT%H:%M:%SZ')" > signature.txt && \
    chown eaglex:eaglex signature.txt

# Switch to non-root user
USER eaglex

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; from eaglex_v33 import EAGLEX; print('HEALTHY')" || exit 1

# Expose monitoring port
EXPOSE 8080

# Environment variables
ENV EAGLE_MODE=production \
    EAGLE_VERSION=3.3 \
    EAGLE_SEAL=310-70-94 \
    LOG_LEVEL=INFO \
    REDIS_URL=redis://localhost:6379 \
    MONITORING_DURATION=60

# Run EAGLE-X
CMD ["python", "-u", "eaglex_v33.py"]
