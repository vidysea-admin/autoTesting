FROM mcr.microsoft.com/playwright/python:v1.62.0-jammy

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# --------------------------------------------------
# 1. Install system dependencies
# --------------------------------------------------
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

RUN pip install --no-cache-dir uv

WORKDIR /app

# --------------------------------------------------
# 2. Configure Python and uv
# --------------------------------------------------
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

# --------------------------------------------------
# 3. Install locked dependencies
# --------------------------------------------------
COPY pyproject.toml uv.lock ./

RUN mkdir -p /opt/uv-python \
    && uv python install 3.12 \
    && uv sync --frozen --python 3.12 --no-install-project

# --------------------------------------------------
# 4. Copy application and install project
# --------------------------------------------------
COPY . .

RUN uv sync --frozen --python 3.12

# --------------------------------------------------
# 5. Fix and inspect Python permissions
# --------------------------------------------------
RUN chmod -R a+rX /opt/uv-python /opt/venv \
    && echo "========== BUILD DIAGNOSTICS ==========" \
    && echo "--- Build architecture ---" \
    && uname -m \
    && echo "--- Python executable symlink ---" \
    && ls -l /opt/venv/bin/python \
    && echo "--- Resolved Python executable ---" \
    && readlink -f /opt/venv/bin/python \
    && echo "--- Python executable permissions ---" \
    && namei -l /opt/venv/bin/python \
    && echo "--- Python directories ---" \
    && ls -ld /opt /opt/uv-python /opt/venv /opt/venv/bin \
    && echo "--- Python runtime test ---" \
    && /opt/venv/bin/python --version \
    && /opt/venv/bin/python -c \
       "import sys; print('Executable:', sys.executable); print('Version:', sys.version)" \
    && echo "--- Application import test ---" \
    && /opt/venv/bin/python -c \
       "import autotester; print('autotester import successful')" \
    && echo "========== BUILD CHECKS PASSED =========="

# --------------------------------------------------
# 6. Copy and validate the application entrypoint
# --------------------------------------------------
COPY docker/entrypoint.sh /entrypoint.sh

RUN chmod 755 /entrypoint.sh \
    && test -s /entrypoint.sh \
    && bash -n /entrypoint.sh \
    && echo "--- Entrypoint validation ---" \
    && ls -l /entrypoint.sh \
    && head -n 1 /entrypoint.sh

# --------------------------------------------------
# 7. Create non-root runtime user
# --------------------------------------------------
RUN groupadd --gid 10001 autotester \
    && useradd --uid 10001 --gid 10001 --create-home autotester \
    && mkdir -p /data /home/autotester/.cache \
    && chown -R 10001:10001 /data /home/autotester/.cache \
    && chmod 755 /data

ENV HOME=/home/autotester \
    XDG_CACHE_HOME=/home/autotester/.cache

# --------------------------------------------------
# 8. Runtime-user validation during image build
# --------------------------------------------------
USER 10001:10001

RUN set -eu; \
    echo "========== NON-ROOT USER CHECK =========="; \
    id; \
    echo "--- Python target ---"; \
    PYTHON_REAL="$(readlink -f /opt/venv/bin/python)"; \
    echo "$PYTHON_REAL"; \
    test -x /opt/venv/bin/python; \
    test -x "$PYTHON_REAL"; \
    /opt/venv/bin/python --version; \
    /opt/venv/bin/python -c \
      "import autotester, os, sys; print('uid:', os.getuid()); print('python:', sys.executable); print('application import: OK')"; \
    echo "--- Writable-directory check ---"; \
    touch /data/.write-test; \
    rm /data/.write-test; \
    touch /home/autotester/.cache/.write-test; \
    rm /home/autotester/.cache/.write-test; \
    echo "========== RUNTIME USER CHECKS PASSED =========="

# --------------------------------------------------
# 9. Runtime diagnostics wrapper
# --------------------------------------------------
USER root

RUN cat > /startup-diagnostics.sh <<'EOF'
#!/bin/bash
set -eu

echo "========== CONTAINER STARTUP DIAGNOSTICS =========="
date -u
id
echo "Working directory: $(pwd)"
echo "PORT=${PORT:-not-set}"

echo "--- Entrypoint ---"
ls -l /entrypoint.sh
test -r /entrypoint.sh
test -x /entrypoint.sh
bash -n /entrypoint.sh

echo "--- Python executable ---"
ls -l /opt/venv/bin/python
PYTHON_REAL="$(readlink -f /opt/venv/bin/python)"
echo "Resolved path: ${PYTHON_REAL}"
namei -l /opt/venv/bin/python
test -x /opt/venv/bin/python
test -x "${PYTHON_REAL}"
/opt/venv/bin/python --version

echo "--- Application import ---"
/opt/venv/bin/python -c \
  "import sys, autotester; print('Python:', sys.executable); print('Application import: OK')"

echo "--- Required directories ---"
for path in /app /data /home/autotester/.cache; do
    if [ -d "$path" ]; then
        ls -ld "$path"
    else
        echo "ERROR: Missing directory: $path"
        exit 1
    fi
done

echo "--- Environment configuration ---"
if [ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]; then
    echo "GOOGLE_APPLICATION_CREDENTIALS is set."
else
    echo "GOOGLE_APPLICATION_CREDENTIALS is not set; ADC may still be available."
fi

# Do not print environment values or .env contents.
if [ -f /app/.env ]; then
    echo "/app/.env exists."
else
    echo "/app/.env does not exist at container startup."
    echo "If .env is downloaded from GCS, verify the entrypoint downloads it."
fi

echo "========== STARTING APPLICATION ENTRYPOINT =========="
exec "$@"
EOF

RUN chmod 755 /startup-diagnostics.sh

USER 10001:10001

# --------------------------------------------------
# 10. Launch diagnostics before the real entrypoint
# --------------------------------------------------
EXPOSE 8000 6080 6081

ENTRYPOINT ["/startup-diagnostics.sh"]
CMD ["/entrypoint.sh"]
