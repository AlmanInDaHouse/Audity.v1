FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl fonts-dejavu-core libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 libcairo2 \
    libgdk-pixbuf-2.0-0 libffi-dev libfontconfig1 libglib2.0-0 libharfbuzz0b libharfbuzz-subset0 shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /workspace/worker
COPY backend /workspace/backend
COPY catalogs /workspace/catalogs
COPY worker/pyproject.toml /workspace/worker/pyproject.toml
RUN uv sync --no-dev

COPY worker /workspace/worker
