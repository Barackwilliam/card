#!/usr/bin/env bash
# Hatua za kujenga kwenye Render (Build Command = ./build.sh)
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py hakikisha_msimamizi
if [ -n "$HARUSI_MALIPO" ]; then
  # Isizuie deploy ikishindwa: ukurasa wa "Anzisha harusi" utaonyesha kosa halisi.
  python manage.py anzisha_harusi --malipo "$HARUSI_MALIPO" || echo "ONYO: kuanzisha harusi kumeshindwa; fungua mfumo uone kosa."
fi

# Worker ya WhatsApp (Baileys) inakimbia ndani ya huduma hii hii (angalia start.sh).
if [ "${WHATSAPP_BACKEND:-}" = "baileys" ]; then
  ./scripts/hakikisha_node.sh
  export PATH="$PWD/.node/bin:$PATH"
  (cd whatsapp-worker && npm ci --omit=dev --no-audit --no-fund)
fi
