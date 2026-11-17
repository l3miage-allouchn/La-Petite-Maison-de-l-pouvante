import pytest

from app.model import build_recommender
from app.model.cooccurrence import CooccurrenceRecommender
from app.store import MemoryFeatureStore
from tests.conftest import NOW, make_event

HOUR = 3600.0


async def view_all(
    recommender: CooccurrenceRecommender,
    *product_ids: str,
    user: str | None = "user-1",
    session: str = "session-0001",
    start: float = NOW - 3 * HOUR,
) -> None:
    for i, pid in enumerate(product_ids):
        await recommender.update(make_event(pid, user_id=user, session_id=session, ts=start + i * 60))


async def test_cold_start_returns_most_popular(recommender: CooccurrenceRecommender) -> None:
    await view_all(recommender, "bluray-suspiria-4k", user=None, session="session-a0001")
    await view_all(recommender, "bluray-suspiria-4k", "fig-nosferatu", user=None, session="session-b0001")

    assert await recommender.recommend("newcomer", 2) == ["bluray-suspiria-4k", "fig-nosferatu"]


async def test_cold_start_without_any_data_uses_catalog(recommender: CooccurrenceRecommender) -> None:
    items = await recommender.recommend("newcomer", 3)
    assert len(items) == 3


async def test_recommendations_follow_category_affinity_and_exclude_viewed(
    recommender: CooccurrenceRecommender,
) -> None:
    # The phase 3 acceptance scenario: a user looks at three figurines.
    await view_all(recommender, "fig-orc-evil-ed", "fig-nosferatu", "fig-masque-hockey")

    items = await recommender.recommend("user-1", 4)

    assert set(items).isdisjoint({"fig-orc-evil-ed", "fig-nosferatu", "fig-masque-hockey"})
    assert {"fig-orc-chaman-evil-ed", "fig-cthulhu-reveil"} <= set(items)  # other figurines
    assert len(items) == 4


async def test_cooccurrence_from_other_viewers_drives_recommendations(
    recommender: CooccurrenceRecommender,
) -> None:
    # Many anonymous visitors view Suspiria then the giallo fanzine.
    for i in range(5):
        await view_all(recommender, "bluray-suspiria-4k", "fanzine-38-giallo", user=None, session=f"session-x{i:04d}")
    await view_all(recommender, "bluray-suspiria-4k")

    assert (await recommender.recommend("user-1", 1)) == ["fanzine-38-giallo"]


async def test_similar_prefers_cooccurrence_then_universe_and_never_returns_itself(
    recommender: CooccurrenceRecommender,
) -> None:
    await view_all(recommender, "fig-nosferatu", "bd-orc-tome1", user=None, session="session-s0001")

    items = await recommender.similar("fig-nosferatu", 3)

    assert "fig-nosferatu" not in items
    assert items[0] == "bd-orc-tome1"  # co-viewed
    assert "bluray-nosferatu-1922" in items  # same universe (gothique)


async def test_similar_for_unknown_product_falls_back_to_popular(recommender: CooccurrenceRecommender) -> None:
    await view_all(recommender, "bluray-suspiria-4k", user=None, session="session-p0001")
    assert (await recommender.similar("unknown-product", 1)) == ["bluray-suspiria-4k"]


async def test_cooccurrence_is_symmetric_and_recency_weighted(catalog_store: MemoryFeatureStore) -> None:
    recommender = CooccurrenceRecommender(catalog_store, half_life_hours=1, clock=lambda: NOW)
    await recommender.update(make_event("fig-nosferatu", ts=NOW))
    await recommender.update(make_event("bluray-nosferatu-1922", ts=NOW + HOUR))  # one half-life later

    forward = dict(await catalog_store.get_cooccurrences("fig-nosferatu", 5))
    backward = dict(await catalog_store.get_cooccurrences("bluray-nosferatu-1922", 5))
    assert forward["bluray-nosferatu-1922"] == pytest.approx(0.5)
    assert backward["fig-nosferatu"] == pytest.approx(0.5)


async def test_recent_views_weigh_more_than_old_ones(catalog_store: MemoryFeatureStore) -> None:
    recommender = CooccurrenceRecommender(catalog_store, half_life_hours=24, clock=lambda: NOW)
    # Old interest in giallo (10 days ago), recent interest in heroic fantasy.
    await recommender.update(make_event("bluray-suspiria-4k", ts=NOW - 240 * HOUR))
    await recommender.update(make_event("fig-orc-evil-ed", ts=NOW - HOUR))

    items = await recommender.recommend("user-1", 2)
    assert items[0] in {"fig-orc-chaman-evil-ed", "bd-orc-tome1"}


async def test_anonymous_views_do_not_create_a_user_profile(recommender: CooccurrenceRecommender) -> None:
    await view_all(recommender, "fig-orc-evil-ed", user=None, session="session-anon01")
    assert await recommender._store.get_views("u:user-1", 10) == []
    assert len(await recommender._store.get_views("s:session-anon01", 10)) == 1


def test_registry_builds_known_model_and_rejects_unknown(store: MemoryFeatureStore) -> None:
    assert build_recommender("cooccurrence", store).name == "cooccurrence"
    with pytest.raises(ValueError, match="Unknown RECO_MODEL"):
        build_recommender("deep-magic", store)
