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

# Fast loop: HA button trigger (mtime of /share/wsd_scan_trigger) + mover to Paperless consume.
(
  LAST=$(stat -c %Y /share/wsd_scan_trigger 2>/dev/null || echo 0)
  while :; do
    if [ -f /share/wsd_scan_trigger ]; then
      M=$(stat -c %Y /share/wsd_scan_trigger 2>/dev/null || echo 0)
      if [ "$M" != "$LAST" ]; then
        LAST=$M
        python3 /app/scan_trigger.py >>/data/scan.log 2>&1
      fi
    fi
    for f in /data/scans/*.jpg; do
      [ -f "$f" ] || continue
      b=$(basename "$f")
      docker cp "app_01037a72_wsd_scan_receiver:/data/scans/$b" "/tmp/mv_$b" 2>>/data/scan.log \
        && docker cp "/tmp/mv_$b" "$PAPERLESS_CONTAINER:/usr/src/paperless/consume/$b" 2>>/data/scan.log \
        && docker exec "$PAPERLESS_CONTAINER" chmod 644 "/usr/src/paperless/consume/$b" 2>>/data/scan.log \
        && rm -f "$f" "/tmp/mv_$b" \
        && echo "$(date +%FT%T) moved $b -> paperless consume" >> /data/scan.log
    done
    sleep 2
  done
) &

# Keeper loop: client (WSD probe/subscribe threads) stays alive; cap client.log size.
(
  while :; do
    PID=$(cat /tmp/wsclient.pid 2>/dev/null)
    if [ -z "$PID" ] || ! kill -0 "$PID" 2>/dev/null; then
      python3 /app/client_loop.py >>/data/client.log 2>&1 &
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

exec wsd-scan-receiver
