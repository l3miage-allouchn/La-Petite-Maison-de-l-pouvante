#!/usr/bin/env bash
# Rebuilds every recommendation profile by replaying the whole Kafka history.
# Kafka keeps the events (retention), so the model can be re-trained from scratch at any time:
#   1. stop reco-service (a consumer group can only be reset when it has no active member)
#   2. delete the model state in Valkey (keys reco:*)
#   3. reset the consumer group offsets to the beginning of the topic
#   4. restart reco-service: it re-consumes every event since the beginning
set -euo pipefail

cd "$(dirname "$0")/.."
COMPOSE=(docker compose --env-file .env -f docker-compose.yml)
GROUP="${KAFKA_GROUP_ID:-reco-service}"
TOPIC="${KAFKA_TOPIC:-catalog.product-viewed}"

echo "⏸  Arrêt de reco-service"
"${COMPOSE[@]}" stop reco-service

echo "🧹 Suppression de l'état du modèle dans Valkey (reco:*)"
"${COMPOSE[@]}" exec -T valkey sh -c \
  'valkey-cli --scan --pattern "reco:*" | xargs -r -n 500 valkey-cli del > /dev/null'

echo "⏮  Remise à zéro des offsets du groupe $GROUP sur $TOPIC"
"${COMPOSE[@]}" exec -T kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --group "$GROUP" --topic "$TOPIC" \
  --reset-offsets --to-earliest --execute

echo "▶️  Redémarrage de reco-service (rejeu de tout l'historique)"
"${COMPOSE[@]}" up -d --wait reco-service
sleep 3
curl -s "http://localhost:${RECO_HOST_PORT:-8082}/metrics/" | grep '^reco_events_consumed_total' || true
echo "✅ Rejeu terminé."
