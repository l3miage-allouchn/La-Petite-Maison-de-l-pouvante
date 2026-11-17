#!/usr/bin/env bash
# Publishes one sample product-viewed event into the local Kafka (Compose stack).
# Usage: ./infra/local/kafka/produce-demo-event.sh [product_id] [session_id]
set -euo pipefail

PRODUCT_ID="${1:-demo-orc-figurine}"
SESSION_ID="${2:-demo-session-$RANDOM}"
EVENT_ID="$(uuidgen | tr '[:upper:]' '[:lower:]')"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

payload=$(printf '{"event_id":"%s","event_type":"product.viewed","occurred_at":"%s","user_id":null,"session_id":"%s","product_id":"%s","category":"FIGURINE","universe":"heroic-fantasy","source":"product_page"}' \
  "$EVENT_ID" "$NOW" "$SESSION_ID" "$PRODUCT_ID")

printf '%s|%s\n' "$SESSION_ID" "$payload" | docker compose exec -T kafka \
  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server localhost:9092 \
  --topic catalog.product-viewed \
  --reader-property parse.key=true --reader-property key.separator='|'

echo "✅ Événement publié (clé=$SESSION_ID) — voir http://localhost:${KAFKA_UI_HOST_PORT:-8085}"
