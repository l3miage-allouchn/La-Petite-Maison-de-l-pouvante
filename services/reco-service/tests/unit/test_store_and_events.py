import pytest
from pydantic import ValidationError

from app.events import ProductViewedEvent
from app.logging_setup import sanitize_correlation_id
from app.store import MemoryFeatureStore, ProductMeta
from tests.conftest import make_event


async def test_history_keeps_latest_timestamp_and_is_trimmed(store: MemoryFeatureStore) -> None:
    for i, pid in enumerate(["a1", "b2", "c3", "a1"]):
        await store.add_view("u:x", pid, 100.0 + i, max_history=2)

    views = await store.get_views("u:x", 10)
    assert [v.product_id for v in views] == ["a1", "c3"]
    assert views[0].timestamp == 103.0


async def test_event_dedup_markers(store: MemoryFeatureStore) -> None:
    assert not await store.is_event_seen("e1")
    await store.mark_event_seen("e1")
    assert await store.is_event_seen("e1")


async def test_popularity_buckets(store: MemoryFeatureStore) -> None:
    await store.register_product(ProductMeta("p0", "BD", "giallo"))
    await store.incr_popularity(ProductMeta("p1", "BD", "giallo"))
    await store.incr_popularity(ProductMeta("p1", "BD", "giallo"))
    await store.incr_popularity(ProductMeta("p2", "FANZINE", "slasher"))

    assert await store.top_popular(2) == [("p1", 2.0), ("p2", 1.0)]
    assert await store.top_popular(5, category="BD") == [("p1", 2.0), ("p0", 0.0)]
    assert await store.top_popular(5, universe="slasher") == [("p2", 1.0)]
    assert (await store.get_product_meta(["p0", "missing"])) == {"p0": ProductMeta("p0", "BD", "giallo")}
    assert await store.ping()


def test_event_viewer_key() -> None:
    assert make_event("fig-nosferatu", user_id="abc").viewer_key == "u:abc"
    assert make_event("fig-nosferatu", user_id=None, session_id="session-zz01").viewer_key == "s:session-zz01"


@pytest.mark.parametrize(
    "override",
    [
        {"event_type": "product.bought"},
        {"product_id": "DROP TABLE"},
        {"session_id": "x"},
        {"category": "TOASTER"},
        {"occurred_at": "2026-11-17T10:00:00"},  # no timezone
        {"unexpected": "field"},
    ],
)
def test_invalid_events_are_rejected(override: dict[str, str]) -> None:
    raw = make_event("fig-nosferatu").model_dump(mode="json")
    raw.update(override)
    with pytest.raises(ValidationError):
        ProductViewedEvent.model_validate(raw)


def test_correlation_id_sanitizing() -> None:
    assert sanitize_correlation_id("demo-0001-abcd") == "demo-0001-abcd"
    generated = sanitize_correlation_id("evil\nline")
    assert "\n" not in generated
    assert len(generated) == 36
    assert len(sanitize_correlation_id(None)) == 36
