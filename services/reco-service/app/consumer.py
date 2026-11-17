"""Kafka consumer: at-least-once, commit after processing, poison messages to the DLQ.

* Invalid message (bad JSON / schema)  -> sent to the DLQ with diagnostic headers, then committed.
* Duplicate event_id                   -> skipped (idempotent).
* Transient error (Valkey unreachable) -> retried with backoff; the offset is NOT committed meanwhile.
"""

import asyncio
import contextlib
import enum
import json
import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, ConsumerRecord, TopicPartition
from pydantic import ValidationError

from app.config import Settings
from app.events import ProductViewedEvent
from app.logging_setup import correlation_id_var, sanitize_correlation_id
from app.metrics import CONSUMER_ERRORS, EVENT_PROCESSING, EVENTS_CONSUMED
from app.model.base import Recommender
from app.store.base import FeatureStore

log = logging.getLogger(__name__)

Headers = Sequence[tuple[str, bytes]]
DlqSender = Callable[[bytes | None, bytes | None, list[tuple[str, bytes]]], Awaitable[None]]


class Outcome(enum.StrEnum):
    PROCESSED = "processed"
    DUPLICATE = "duplicate"
    DLQ = "dlq"


def _header(headers: Headers, name: str) -> str | None:
    for key, value in headers:
        if key == name:
            return value.decode("utf-8", errors="replace")
    return None


class EventHandler:
    """Pure processing logic, independent from the Kafka client (unit-testable)."""

    def __init__(self, recommender: Recommender, store: FeatureStore, send_to_dlq: DlqSender) -> None:
        self._recommender = recommender
        self._store = store
        self._send_to_dlq = send_to_dlq

    async def handle(self, key: bytes | None, value: bytes | None, headers: Headers, source: str) -> Outcome:
        correlation_id_var.set(sanitize_correlation_id(_header(headers, "correlation_id")))
        try:
            event = ProductViewedEvent.model_validate(json.loads(value or b""))
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
            reason = type(exc).__name__
            dlq_headers = [*headers, ("dlq_reason", reason.encode()), ("dlq_source", source.encode())]
            await self._send_to_dlq(key, value, list(dlq_headers))
            EVENTS_CONSUMED.labels(Outcome.DLQ).inc()
            log.warning("invalid event sent to DLQ source=%s reason=%s", source, reason)
            return Outcome.DLQ

        if await self._store.is_event_seen(str(event.event_id)):
            EVENTS_CONSUMED.labels(Outcome.DUPLICATE).inc()
            log.info("duplicate event skipped event_id=%s", event.event_id)
            return Outcome.DUPLICATE

        started = time.perf_counter()
        await self._recommender.update(event)
        # Marked only once applied: a failure above is retried instead of being taken for a duplicate.
        await self._store.mark_event_seen(str(event.event_id))
        EVENT_PROCESSING.observe(time.perf_counter() - started)
        EVENTS_CONSUMED.labels(Outcome.PROCESSED).inc()
        log.info("event processed product_id=%s authenticated=%s", event.product_id, event.user_id is not None)
        return Outcome.PROCESSED


class EventConsumer:
    """Runs the aiokafka consumer loop as a background task of the FastAPI app."""

    def __init__(self, settings: Settings, recommender: Recommender, store: FeatureStore) -> None:
        self._settings = settings
        self._consumer = AIOKafkaConsumer(
            settings.kafka_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            client_id="reco-service",
        )
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            acks="all",
            enable_idempotence=True,
            client_id="reco-service-dlq",
        )
        self._handler = EventHandler(recommender, store, self._send_to_dlq)
        self._task: asyncio.Task[None] | None = None
        self.running = False

    async def _send_to_dlq(self, key: bytes | None, value: bytes | None, headers: list[tuple[str, bytes]]) -> None:
        await self._producer.send_and_wait(self._settings.kafka_dlq_topic, value=value, key=key, headers=headers)

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="kafka-consumer")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _connect(self) -> None:
        backoff = 1.0
        while True:
            try:
                await self._producer.start()
                await self._consumer.start()
                return
            except Exception as exc:  # broker not ready yet
                CONSUMER_ERRORS.labels("connect").inc()
                log.warning("Kafka not reachable (%s), retrying in %.0fs", exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    async def _run(self) -> None:
        await self._connect()
        self.running = True
        log.info("consumer started topic=%s group=%s", self._settings.kafka_topic, self._settings.kafka_group_id)
        try:
            while True:
                batch: dict[TopicPartition, list[ConsumerRecord[Any, Any]]] = await self._consumer.getmany(
                    timeout_ms=1000, max_records=100
                )
                for tp, records in batch.items():
                    for record in records:
                        await self._handle_with_retry(record)
                    await self._consumer.commit({tp: records[-1].offset + 1})
        finally:
            self.running = False
            await self._consumer.stop()
            await self._producer.stop()

    async def _handle_with_retry(self, record: ConsumerRecord[Any, Any]) -> None:
        source = f"{record.topic}-{record.partition}-{record.offset}"
        backoff = 0.5
        while True:
            try:
                await self._handler.handle(record.key, record.value, record.headers or [], source)
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # transient (store down, DLQ unreachable): retry, never skip
                CONSUMER_ERRORS.labels(type(exc).__name__).inc()
                log.error("event processing failed source=%s (%s), retrying in %.1fs", source, exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10.0)
