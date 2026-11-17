"""Kafka -> consumer -> Valkey -> recommendations, with real infrastructure (Testcontainers)."""

import asyncio
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from valkey.asyncio import Valkey

from app.config import Settings
from app.consumer import EventConsumer
from app.model.cooccurrence import CooccurrenceRecommender
from app.store import ProductMeta
from app.store.valkey_store import ValkeyFeatureStore
from tests.conftest import CATALOG, NOW, make_event

pytestmark = pytest.mark.integration

TOPIC = "catalog.product-viewed"
DLQ = "catalog.product-viewed.dlq"


@pytest.fixture
async def valkey_store(valkey_address: tuple[str, int]) -> AsyncIterator[ValkeyFeatureStore]:
    host, port = valkey_address
    client = Valkey(host=host, port=port, decode_responses=True)
    prefix = f"it-{uuid.uuid4().hex[:8]}:"  # isolates each test
    store = ValkeyFeatureStore(client, prefix)
    for meta in CATALOG:
        await store.register_product(meta)
    yield store
    await client.aclose()


async def eventually(check: Callable[[], Awaitable[bool]], within_s: float = 30.0) -> None:
    deadline = asyncio.get_running_loop().time() + within_s
    while asyncio.get_running_loop().time() < deadline:
        if await check():
            return
        await asyncio.sleep(0.25)
    raise AssertionError("condition not met in time")


async def test_valkey_store_contract(valkey_store: ValkeyFeatureStore) -> None:
    assert await valkey_store.ping()
    await valkey_store.add_view("u:x", "fig-nosferatu", 100.0, max_history=2)
    await valkey_store.add_view("u:x", "bd-orc-tome1", 101.0, max_history=2)
    await valkey_store.add_view("u:x", "fig-nosferatu", 50.0, max_history=2)  # older: ignored (GT)
    await valkey_store.add_view("u:x", "fanzine-38-giallo", 102.0, max_history=2)
    assert [v.product_id for v in await valkey_store.get_views("u:x", 10)] == ["fanzine-38-giallo", "bd-orc-tome1"]

    await valkey_store.incr_cooccurrence("fig-nosferatu", "bd-orc-tome1", 0.5)
    assert await valkey_store.get_cooccurrences("bd-orc-tome1", 5) == [("fig-nosferatu", 0.5)]

    await valkey_store.incr_popularity(ProductMeta("fig-nosferatu", "FIGURINE", "gothique"))
    assert (await valkey_store.top_popular(1)) == [("fig-nosferatu", 1.0)]
    assert (await valkey_store.top_popular(1, universe="gothique")) == [("fig-nosferatu", 1.0)]
    assert (await valkey_store.get_product_meta(["fig-nosferatu", "nope"]))["fig-nosferatu"].category == "FIGURINE"
    assert await valkey_store.get_product_meta([]) == {}

    assert not await valkey_store.is_event_seen("e-1")
    await valkey_store.mark_event_seen("e-1")
    assert await valkey_store.is_event_seen("e-1")


async def test_consumer_end_to_end(kafka_bootstrap: str, valkey_store: ValkeyFeatureStore) -> None:
    settings = Settings(kafka_bootstrap_servers=kafka_bootstrap, kafka_group_id=f"it-{uuid.uuid4().hex[:6]}")
    recommender = CooccurrenceRecommender(valkey_store, clock=lambda: NOW + 600)
    consumer = EventConsumer(settings, recommender, valkey_store)
    producer = AIOKafkaProducer(bootstrap_servers=kafka_bootstrap)
    await producer.start()
    await consumer.start()
    try:
        # nesrine views three figurines (the phase 3 acceptance scenario) ...
        events = [
            make_event(pid, user_id="nesrine-it", ts=NOW + i)
            for i, pid in enumerate(["fig-orc-evil-ed", "fig-nosferatu", "fig-masque-hockey"])
        ]
        for event in events:
            await producer.send_and_wait(
                TOPIC,
                event.model_dump_json().encode(),
                key=b"nesrine-it",
                headers=[("correlation_id", b"it-corr-0001")],
            )
        # ... the same event is delivered twice, and one poison message arrives.
        await producer.send_and_wait(TOPIC, events[0].model_dump_json().encode(), key=b"nesrine-it")
        await producer.send_and_wait(TOPIC, b"{broken json", key=b"poison")

        async def all_applied() -> bool:
            return len(await valkey_store.get_views("u:nesrine-it", 10)) == 3

        await eventually(all_applied)
        await asyncio.sleep(1.5)  # leave time for the duplicate and the poison message

        items = await recommender.recommend("nesrine-it", 4)
        assert {"fig-orc-chaman-evil-ed", "fig-cthulhu-reveil"} <= set(items)
        assert set(items).isdisjoint({e.product_id for e in events})
        # duplicate ignored: popularity counted once
        assert dict(await valkey_store.top_popular(10))["fig-orc-evil-ed"] == 1.0
        assert consumer.running

        dlq = AIOKafkaConsumer(
            DLQ,
            bootstrap_servers=kafka_bootstrap,
            auto_offset_reset="earliest",
            group_id=f"it-dlq-{uuid.uuid4().hex[:6]}",
        )
        await dlq.start()
        try:
            record = await asyncio.wait_for(dlq.getone(), timeout=20)
        finally:
            await dlq.stop()
        assert record.value == b"{broken json"
        assert dict(record.headers)["dlq_reason"] == b"JSONDecodeError"
    finally:
        await consumer.stop()
        await producer.stop()
