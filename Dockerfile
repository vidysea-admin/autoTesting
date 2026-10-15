# Contract: qa/contracts/docker.md D1-D2. Playwright's own image ships Chromium plus every
# Linux font/codec dependency it needs, so this file only adds the pieces that turn a headless
# container into one with a virtual display and a web-reachable viewer onto it.
FROM mcr.microsoft.com/playwright/python:v1.62.0-jammy

# Without these, tzdata (pulled in transitively by novnc/websockify) prompts interactively for a
# timezone at install time -- apt-get -y answers confirmations but not debconf prompts, so the
# build hangs forever with no error (found running this for real: a 2.767GB image had pulled fine,
# then apt-get sat with rising CPU and zero progress for over an hour).
ENV DEBIAN_FRONTEND=noninteractive TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    xvfb x11vnc novnc websockify curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

# Keep the frozen environment outside the source tree (also for dev bind mounts).
ENV UV_PROJECT_ENVIRONMENT=/opt/venv PYTHONDONTWRITEBYTECODE=1
ENV UV_PYTHON=3.13
ENV UV_PYTHON_DOWNLOADS=never

# Dependencies first so `uv sync` layers cache across code-only changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --python 3.13 --no-install-project

COPY . .
RUN uv sync --frozen --python 3.13

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Source and dependencies remain root-owned. Only home/cache and /data are writable.
RUN groupadd --gid 10001 autotester \
    && useradd --uid 10001 --gid 10001 --create-home autotester \
    && mkdir -p /data /home/autotester/.cache \
    && chown 10001:10001 /data /home/autotester/.cache
ENV HOME=/home/autotester XDG_CACHE_HOME=/home/autotester/.cache UV_NO_SYNC=1
USER 10001:10001

ENV DISPLAY=:99
EXPOSE 8000 6080 6081

ENTRYPOINT ["/entrypoint.sh"]
