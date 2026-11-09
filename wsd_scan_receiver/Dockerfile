FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends docker-cli \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    DOCKER_HOST=unix:///run/docker.sock \
    PYTHONUNBUFFERED=1 \
    OUTPUT_DIR=/data/scans \
    ORIGINAL_DIR=/data/originals \
    RAW_DUMP_DIR=/data/debug-dumps \
    DATA_DIR=/data \
    WSD_HTTP_PORT=5357 \
    WSD_ADMIN_PORT=8888

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts

RUN pip install --no-cache-dir .

RUN chmod +x /app/scripts/run.sh /app/scripts/mover.sh 2>/dev/null || true

CMD ["sh", "-c", "exec /app/scripts/run.sh"]

EXPOSE 5357/tcp
EXPOSE 8888/tcp
EXPOSE 3702/udp

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os; from urllib.request import urlopen; urlopen(f'http://127.0.0.1:{os.getenv(\"WSD_HTTP_PORT\", \"5357\")}/healthz', timeout=3).read()"
