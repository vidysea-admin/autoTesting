FROM mcr.microsoft.com/playwright/python:v1.62.0-jammy

ENV DEBIAN_FRONTEND=noninteractive TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    xvfb x11vnc novnc websockify curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PYTHON=3.12

COPY pyproject.toml uv.lock ./

RUN uv python install 3.12 \
    && uv sync --frozen --python 3.12 --no-install-project

COPY . .

RUN uv sync --frozen --python 3.12

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN groupadd --gid 10001 autotester \
    && useradd --uid 10001 --gid 10001 --create-home autotester \
    && mkdir -p /data /home/autotester/.cache \
    && chown 10001:10001 /data /home/autotester/.cache

ENV HOME=/home/autotester \
    XDG_CACHE_HOME=/home/autotester/.cache \
    UV_NO_SYNC=1 \
    DISPLAY=:99

USER 10001:10001

EXPOSE 8000 6080 6081

ENTRYPOINT ["/entrypoint.sh"]
