#!/bin/sh
# Self-contained WSD receiver entrypoint: server (foreground) + trigger/mover
# loop + client-loop keeper (background). Survives HA host reboot via boot: auto.
umask 022
mkdir -p /data/scans /data/originals /data/debug-dumps
export WSD_DEVICE_NAME="${DEVICE_NAME:-Paperless}" \
       WSD_HOSTNAME="${DEVICE_HOSTNAME:-Paperless}" \
       WSD_SCANNER_IP="${SCANNER_IP:-}" \
       WSD_SUBSCRIBE_ENABLED="${SUBSCRIBE_ENABLED:-false}" \
       WSD_SUBSCRIBE_INTERVAL_SECONDS="${SUBSCRIBE_INTERVAL:-60}" \
       WSD_DEBUG="${DEBUG:-false}" \
       LOG_LEVEL="${LOG_LEVEL:-info}"
PAPERLESS_CONTAINER=$(python3 -c "import json; print(json.load(open('/data/options.json')).get('paperless_container', 'app_55eca821_paperless-ngx'))" 2>/dev/null)
PAPERLESS_CONTAINER="${PAPERLESS_CONTAINER:-app_55eca821_paperless-ngx}"
# The Paperless add-on's consumer daemon watches its CONSUMPTION_DIR, which is
# /share/paperless/consume in this add-on image (not the image default path).
CONSUME_DIR=$(python3 -c "import json; print(json.load(open('/data/options.json')).get('consume_path', '/share/paperless/consume'))" 2>/dev/null)
CONSUME_DIR="${CONSUME_DIR:-/share/paperless/consume}"
MULTI_TIMEOUT=240

# Fast loop: HA button trigger (mtime of /share/wsd_scan_trigger) + mover to Paperless consume.
# Multi-page batches (/data/multi_pending.json) are collected until the armed
# page count arrived, then merged into ONE PDF and delivered as a single doc.
(
  LAST=$(stat -c %Y /share/wsd_scan_trigger 2>/dev/null || echo 0)
  while :; do
    if [ -f /share/wsd_scan_trigger ]; then
      M=$(stat -c %Y /share/wsd_scan_trigger 2>/dev/null || echo 0)
      if [ "$M" != "$LAST" ]; then
        LAST=$M
        python3 /app/scripts/scan_trigger.py >>/data/scan.log 2>&1
      fi
    fi

    PAGES=0
    ARMED=0
    if [ -f /data/multi_pending.json ]; then
      PAGES=$(python3 -c "import json;print(json.load(open('/data/multi_pending.json')).get('pages',0))" 2>/dev/null || echo 0)
      ARMED=$(python3 -c "import json;print(json.load(open('/data/multi_pending.json')).get('armed',0))" 2>/dev/null || echo 0)
    fi

    if [ "$PAGES" -gt 1 ]; then
      N=$(ls /data/scans/*.jpg 2>/dev/null | wc -l)
      AGE=$(( $(date +%s) - ARMED ))
      if [ "$N" -ge "$PAGES" ] || [ "$AGE" -gt "$MULTI_TIMEOUT" ]; then
        out="/data/scans/scan-multi-$(date +%Y%m%dT%H%M%S).pdf"
        if python3 /app/scripts/pdf_merge.py "$out" /data/scans/*.jpg >>/data/scan.log 2>&1; then
          b=$(basename "$out")
          docker cp "app_01037a72_wsd_scan_receiver:$out" "/tmp/mv_$b" 2>>/data/scan.log \
            && docker cp "/tmp/mv_$b" "$PAPERLESS_CONTAINER:$CONSUME_DIR/$b" 2>>/data/scan.log \
            && docker exec "$PAPERLESS_CONTAINER" chmod 644 "$CONSUME_DIR/$b" 2>>/data/scan.log \
            && rm -f "$out" "/tmp/mv_$b" /data/scans/*.jpg /data/multi_pending.json \
            && echo "$(date +%FT%T) merged batch of $N -> $b -> paperless consume" >> /data/scan.log
        else
          rm -f /data/multi_pending.json
          echo "$(date +%FT%T) batch merge FAILED, falling back to single delivery" >> /data/scan.log
        fi
      fi
    fi

    if [ "$PAGES" -le 1 ]; then
      for f in /data/scans/*.jpg; do
        [ -f "$f" ] || continue
        b=$(basename "$f")
        docker cp "app_01037a72_wsd_scan_receiver:/data/scans/$b" "/tmp/mv_$b" 2>>/data/scan.log \
          && docker cp "/tmp/mv_$b" "$PAPERLESS_CONTAINER:$CONSUME_DIR/$b" 2>>/data/scan.log \
          && docker exec "$PAPERLESS_CONTAINER" chmod 644 "$CONSUME_DIR/$b" 2>>/data/scan.log \
          && rm -f "$f" "/tmp/mv_$b" \
          && echo "$(date +%FT%T) moved $b -> paperless consume" >> /data/scan.log
      done
    fi
    sleep 2
  done
) &

# Keeper loop: client (WSD probe/subscribe threads) stays alive; cap client.log size.
(
  while :; do
    PID=$(cat /tmp/wsclient.pid 2>/dev/null)
    if [ -z "$PID" ] || ! kill -0 "$PID" 2>/dev/null; then
      python3 /app/scripts/client_loop.py >>/data/client.log 2>&1 &
      echo $! > /tmp/wsclient.pid
    fi
    if [ -f /data/client.log ]; then
      sz=$(wc -c </data/client.log)
      if [ "$sz" -gt 5000000 ]; then
        tail -c 200000 /data/client.log > /data/client.log.tmp && mv /data/client.log.tmp /data/client.log
      fi
    fi
    sleep 30
  done
) &

# Multi-scan control server (port 18125): HA button 2 arms page-count batches.
(
  while :; do
    PID=$(cat /tmp/multisrv.pid 2>/dev/null)
    if [ -z "$PID" ] || ! kill -0 "$PID" 2>/dev/null; then
      python3 /app/scripts/multi_server.py >>/data/scan.log 2>&1 &
      echo $! > /tmp/multisrv.pid
    fi
    sleep 30
  done
) &

exec wsd-scan-receiver
