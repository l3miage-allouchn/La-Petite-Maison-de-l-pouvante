#!/usr/bin/env bash
# Idempotent topic creation, run once by the `kafka-init` Compose service.
set -euo pipefail

BOOTSTRAP="${KAFKA_BOOTSTRAP:-kafka:19092}"
TOPICS_BIN=/opt/kafka/bin/kafka-topics.sh

create_topic() {
  local name="$1" partitions="$2"
  "$TOPICS_BIN" --bootstrap-server "$BOOTSTRAP" --create --if-not-exists \
    --topic "$name" --partitions "$partitions" --replication-factor 1
}

create_topic catalog.product-viewed 3
create_topic catalog.product-viewed.dlq 1

echo "Topics:"
"$TOPICS_BIN" --bootstrap-server "$BOOTSTRAP" --describe \
  --topic 'catalog\.product-viewed.*'
