# Olivas Power System Studio — v2.0.0 Dockerfile
# Reproducible build for headless analysis runs.

FROM python:3.11-slim

LABEL org.opencontainers.image.title="Olivas Power System Studio"
LABEL org.opencontainers.image.version="2.0.0"
LABEL org.opencontainers.image.source="https://github.com/landerson/olivas"
LABEL org.opencontainers.image.licenses="Proprietary"

# System deps for matplotlib + Qt offscreen
RUN apt-get update && apt-get install -y --no-install-recommends \
        libxkbcommon0 \
        libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
        libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
        libxcb-sync1 libxcb-xfixes0 libxcb-xinerama0 \
        libxcb-xkb1 libdbus-1-3 libfontconfig1 libegl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Layer 1: dependencies (cacheable)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Layer 2: source
COPY app /app/app
COPY tests /app/tests
COPY docs /app/docs

# Default: headless mode (sem GUI)
ENV QT_QPA_PLATFORM=offscreen
ENV PYTHONPATH=/app
ENV OLIVAS_HEADLESS=1

# Healthcheck: importa app
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from app.core.version import VERSION; print(VERSION)" || exit 1

# Default entrypoint: roda testes (CI mode)
# Override com `docker run olivas python -m app` para runtime
ENTRYPOINT ["python", "-m", "pytest"]
CMD ["tests/", "-q", "--tb=short"]
