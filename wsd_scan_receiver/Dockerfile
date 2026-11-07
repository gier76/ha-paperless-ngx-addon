FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OUTPUT_DIR=/data/scans \
    ORIGINAL_DIR=/share/paperless/original \
    RAW_DUMP_DIR=/data/debug-dumps \
    DATA_DIR=/data \
    WSD_HTTP_PORT=5357 \
    WSD_ADMIN_PORT=8888

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

CMD ["sh", "-c", "mkdir -p /share/paperless/consume /share/paperless/original /data/debug-dumps; export WSD_DEVICE_NAME=\"${DEVICE_NAME:-Paperless}\" WSD_HOSTNAME=\"${DEVICE_HOSTNAME:-Paperless}\" WSD_SCANNER_IP=\"${SCANNER_IP:-}\" WSD_SUBSCRIBE_ENABLED=\"${SUBSCRIBE_ENABLED:-false}\" WSD_SUBSCRIBE_INTERVAL_SECONDS=\"${SUBSCRIBE_INTERVAL:-60}\" WSD_DEBUG=\"${DEBUG:-false}\" LOG_LEVEL=\"${LOG_LEVEL:-info}\"; umask 022; exec wsd-scan-receiver"]

EXPOSE 5357/tcp
EXPOSE 8888/tcp
EXPOSE 3702/udp

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os; from urllib.request import urlopen; urlopen(f'http://127.0.0.1:{os.getenv(\"WSD_HTTP_PORT\", \"5357\")}/healthz', timeout=3).read()"
