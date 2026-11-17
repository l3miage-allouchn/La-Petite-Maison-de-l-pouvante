import json

import pytest

from app.consumer import EventHandler, Outcome
from app.logging_setup import correlation_id_var
from app.model.cooccurrence import CooccurrenceRecommender
from app.store import MemoryFeatureStore
from tests.conftest import make_event


class FakeDlq:
    def __init__(self) -> None:
        self.messages: list[tuple[bytes | None, bytes | None, list[tuple[str, bytes]]]] = []

    async def __call__(self, key: bytes | None, value: bytes | None, headers: list[tuple[str, bytes]]) -> None:
        self.messages.append((key, value, headers))


@pytest.fixture
def dlq() -> FakeDlq:
    return FakeDlq()


@pytest.fixture
def handler(recommender: CooccurrenceRecommender, catalog_store: MemoryFeatureStore, dlq: FakeDlq) -> EventHandler:
    return EventHandler(recommender, catalog_store, dlq)


async def test_valid_event_is_applied_once(handler: EventHandler, catalog_store: MemoryFeatureStore) -> None:
    event = make_event("fig-nosferatu")
    payload = event.model_dump_json().encode()
    headers = [("correlation_id", b"corr-12345678")]

    assert await handler.handle(b"user-1", payload, headers, "t-0-1") is Outcome.PROCESSED
    assert correlation_id_var.get() == "corr-12345678"
    assert await handler.handle(b"user-1", payload, headers, "t-0-2") is Outcome.DUPLICATE

    assert (await catalog_store.top_popular(1)) == [("fig-nosferatu", 1.0)]


@pytest.mark.parametrize("payload", [b"not json", b"\xff\xfe", json.dumps({"event_type": "product.viewed"}).encode()])
async def test_poison_messages_go_to_dlq_with_diagnostics(handler: EventHandler, dlq: FakeDlq, payload: bytes) -> None:
    outcome = await handler.handle(b"k", payload, [("correlation_id", b"corr-12345678")], "catalog.product-viewed-2-42")

    assert outcome is Outcome.DLQ
    key, value, headers = dlq.messages[0]
    assert (key, value) == (b"k", payload)
    header_map = dict(headers)
    assert header_map["dlq_source"] == b"catalog.product-viewed-2-42"
    assert header_map["dlq_reason"] in {b"JSONDecodeError", b"UnicodeDecodeError", b"ValidationError"}
    assert header_map["correlation_id"] == b"corr-12345678"  # original headers preserved


async def test_failed_update_is_not_marked_as_seen(catalog_store: MemoryFeatureStore, dlq: FakeDlq) -> None:
    class BrokenRecommender(CooccurrenceRecommender):
        async def update(self, event: object) -> None:  # type: ignore[override]
            raise ConnectionError("valkey down")

    handler = EventHandler(BrokenRecommender(catalog_store), catalog_store, dlq)
    event = make_event("fig-nosferatu")

    with pytest.raises(ConnectionError):
        await handler.handle(None, event.model_dump_json().encode(), [], "t-0-1")
    assert not await catalog_store.is_event_seen(str(event.event_id))  # will be retried, not skipped
