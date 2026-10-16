
FROM mcr.microsoft.com/playwright/python:v1.62.0-jammy

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# 1. Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    curl \
    ffmpeg \
    util-linux \
    file \
    && rm -rf /var/lib/apt/lists/*

# 2. Install uv
RUN pip install --no-cache-dir uv

WORKDIR /app

# 3. Python and uv configuration
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_INSTALL_DIR=/opt/uv-python \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_PYTHON_DOWNLOADS=manual \
    UV_NO_SYNC=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON=3.12 \
    PATH="/opt/venv/bin:${PATH}" \
    PORT=8000 \
    DISPLAY=:99

# 4. Install locked dependencies first
COPY pyproject.toml uv.lock ./

RUN mkdir -p /opt/uv-python \
    && uv python install 3.12 \
    && uv sync --frozen --python 3.12 --no-install-project

# 5. Copy application and install project
COPY . .

RUN uv sync --frozen --python 3.12

# 6. Python executable and permission diagnostics
RUN set -eux; \
    chmod -R a+rX /opt/uv-python /opt/venv; \
    echo "========== PYTHON DIAGNOSTICS =========="; \
    uname -m; \
    ls -l /opt/venv/bin/python; \
    readlink -f /opt/venv/bin/python; \
    namei -l /opt/venv/bin/python; \
    ls -ld /opt /opt/uv-python /opt/venv /opt/venv/bin; \
    /opt/venv/bin/python --version; \
    /opt/venv/bin/python -c "import sys; print(sys.executable); print(sys.version)"; \
    /opt/venv/bin/python -c "import autotester; print('autotester import OK')"

# 7. Install and validate entrypoint
COPY docker/entrypoint.sh /entrypoint.sh

RUN set -eux; \
    chmod 755 /entrypoint.sh; \
    test -s /entrypoint.sh; \
    bash -n /entrypoint.sh; \
    echo "========== ENTRYPOINT VALIDATION PASSED =========="; \
    ls -l /entrypoint.sh; \
    head -n 1 /entrypoint.sh

# 8. Create non-root runtime user
RUN groupadd --gid 10001 autotester \
    && useradd --uid 10001 --gid 10001 --create-home autotester \
    && mkdir -p /data /home/autotester/.cache \
    && chown -R 10001:10001 /data /home/autotester/.cache \
    && chmod 755 /data

ENV HOME=/home/autotester \
    XDG_CACHE_HOME=/home/autotester/.cache

# 9. Test Python and writable directories as the runtime user
USER 10001:10001

RUN set -eux; \
    echo "========== NON-ROOT RUNTIME CHECKS =========="; \
    id; \
    PYTHON_REAL="$(readlink -f /opt/venv/bin/python)"; \
    echo "Resolved Python: ${PYTHON_REAL}"; \
    test -x /opt/venv/bin/python; \
    test -x "${PYTHON_REAL}"; \
    /opt/venv/bin/python --version; \
    /opt/venv/bin/python -c "import os, sys, autotester; print('UID:', os.getuid()); print('Python:', sys.executable); print('Application import OK')"; \
    touch /data/.write-test; \
    rm /data/.write-test; \
    touch /home/autotester/.cache/.write-test; \
    rm /home/autotester/.cache/.write-test; \
    echo "========== RUNTIME CHECKS PASSED =========="

# 10. Start diagnostics and then the real application entrypoint
# No heredoc is used, so Dockerfile parsing remains straightforward.
USER root

RUN printf '%s\n' \
    '#!/bin/bash' \
    'set -eu' \
    'echo "========== CONTAINER STARTUP DIAGNOSTICS =========="' \
    'date -u' \
    'id' \
    'echo "PORT=${PORT:-not-set}"' \
    'echo "--- Entrypoint ---"' \
    'ls -l /entrypoint.sh' \
    'bash -n /entrypoint.sh' \
    'echo "--- Python ---"' \
    'ls -l /opt/venv/bin/python' \
    'PYTHON_REAL="$(readlink -f /opt/venv/bin/python)"' \
    'echo "Resolved Python: ${PYTHON_REAL}"' \
    'namei -l /opt/venv/bin/python' \
    'test -x /opt/venv/bin/python' \
    'test -x "${PYTHON_REAL}"' \
    '/opt/venv/bin/python --version' \
    'echo "--- Application import ---"' \
    '/opt/venv/bin/python -c "import sys, autotester; print(sys.executable); print(\"Application import OK\")"' \
    'echo "--- Configuration presence (values hidden) ---"' \
    'if [ -f /app/.env ]; then echo "/app/.env exists"; else echo "/app/.env is absent"; fi' \
    'echo "========== EXECUTING APPLICATION ENTRYPOINT =========="' \
    'exec /entrypoint.sh' \
    > /startup-diagnostics.sh \
    && chmod 755 /startup-diagnostics.sh

# 11. Cloud Run runtime
USER 10001:10001

EXPOSE 8000 6080 6081

ENTRYPOINT ["/startup-diagnostics.sh"]
