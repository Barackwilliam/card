#!/usr/bin/env bash
# Inawasha mfumo (gunicorn) na, kama WHATSAPP_BACKEND=baileys, worker ya WhatsApp
# ndani ya huduma hii hii. Render: Start Command = ./start.sh
export PATH="$PWD/.node/bin:$PATH"
WORKER_PID=""

if [ "${WHATSAPP_BACKEND:-}" = "baileys" ]; then
  (
    cd whatsapp-worker || exit 1
    while true; do
      # PORT ni ya gunicorn; worker isijaribu kuitumia
      env -u PORT node src/index.js &
      child=$!
      trap 'kill -TERM "$child" 2>/dev/null; wait "$child"; exit 0' TERM INT
      wait "$child"
      echo "[start.sh] Worker ya WhatsApp ilisimama; inaanza upya baada ya sekunde 10."
      sleep 10
    done
  ) &
  WORKER_PID=$!
fi

gunicorn config.wsgi --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --timeout 120 &
WEB_PID=$!

zima() {
  echo "[start.sh] Inazima..."
  kill -TERM "$WEB_PID" 2>/dev/null
  [ -n "$WORKER_PID" ] && kill -TERM "$WORKER_PID" 2>/dev/null
  wait
  exit 0
}
trap zima TERM INT

# Gunicorn ikisimama, huduma nzima isimame ili Render iiwashe upya
wait "$WEB_PID"
[ -n "$WORKER_PID" ] && kill -TERM "$WORKER_PID" 2>/dev/null
wait
