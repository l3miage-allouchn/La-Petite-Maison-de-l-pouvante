"""Baseline recommender: co-occurrence + category/universe affinity, weighted by recency.

Simple and explainable, by design:

* Co-occurrence — when a viewer looks at product B shortly after product A, the pair (A, B) gets a
  weight decay(time between the two views). "People who viewed A also viewed B."
* Affinity — a user's recent views (each weighted by decay(age)) give a distribution over categories
  and universes. Popular products of the user's favourite categories/universes get a bonus.
* Recency — decay(age) = 0.5 ** (age / half_life): a view from one half-life ago counts half.
* Cold start — users without history get the globally most viewed products.

score(candidate) = W_COOC * Σ_viewed decay(viewed) * cooc(viewed, candidate) / max_cooc(viewed)
                 + W_UNIVERSE * affinity_universe(candidate) * popularity_in_universe(candidate)
                 + W_CATEGORY * affinity_category(candidate) * popularity_in_category(candidate)
"""

import time
from collections import defaultdict
from collections.abc import Callable

from app.events import ProductViewedEvent, user_key
from app.model.base import Recommender
from app.store.base import FeatureStore, ProductMeta, View

W_COOC = 1.0
W_UNIVERSE = 0.6
W_CATEGORY = 0.4
NEIGHBOURS_PER_PRODUCT = 20
TOP_AFFINITIES = 2


class CooccurrenceRecommender(Recommender):
    name = "cooccurrence"

    def __init__(
        self,
        store: FeatureStore,
        half_life_hours: float = 72.0,
        history_size: int = 20,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._store = store
        self._half_life = half_life_hours * 3600.0
        self._history = history_size
        self._clock = clock

    def _decay(self, age_seconds: float) -> float:
        return float(0.5 ** (max(age_seconds, 0.0) / self._half_life))

    # ------------------------------------------------------------------ learning
    async def update(self, event: ProductViewedEvent) -> None:
        meta = ProductMeta(event.product_id, event.category, event.universe)
        await self._store.incr_popularity(meta)

        previous = await self._store.get_views(event.viewer_key, self._history)
        for view in previous:
            if view.product_id != event.product_id:
                weight = self._decay(abs(event.timestamp - view.timestamp))
                await self._store.incr_cooccurrence(event.product_id, view.product_id, weight)

        await self._store.add_view(event.viewer_key, event.product_id, event.timestamp, self._history)

    # ------------------------------------------------------------------ serving
    async def recommend(self, user_id: str, k: int) -> list[str]:
        views = await self._store.get_views(user_key(user_id), self._history)
        if not views:
            return await self._popular(k, exclude=set())

        now = self._clock()
        weights = {v.product_id: self._decay(now - v.timestamp) for v in views}
        viewed = set(weights)
        scores: dict[str, float] = defaultdict(float)

        await self._add_cooccurrence_scores(scores, weights)
        await self._add_affinity_scores(scores, views, weights)

        ranked = [pid for pid, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])) if pid not in viewed]
        return await self._fill(ranked[:k], k, exclude=viewed)

    async def similar(self, product_id: str, k: int) -> list[str]:
        scores: dict[str, float] = defaultdict(float)
        await self._add_cooccurrence_scores(scores, {product_id: 1.0})

        meta = (await self._store.get_product_meta([product_id])).get(product_id)
        if meta is not None:
            await self._add_bucket_scores(scores, W_UNIVERSE, universe=meta.universe)
            await self._add_bucket_scores(scores, W_CATEGORY, category=meta.category)

        ranked = [pid for pid, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])) if pid != product_id]
        return await self._fill(ranked[:k], k, exclude={product_id})

    # ------------------------------------------------------------------ helpers
    async def _add_cooccurrence_scores(self, scores: dict[str, float], weights: dict[str, float]) -> None:
        for pid, weight in weights.items():
            neighbours = await self._store.get_cooccurrences(pid, NEIGHBOURS_PER_PRODUCT)
            if not neighbours:
                continue
            top = neighbours[0][1] or 1.0
            for other, cooc in neighbours:
                scores[other] += W_COOC * weight * cooc / top

    async def _add_affinity_scores(
        self, scores: dict[str, float], views: list[View], weights: dict[str, float]
    ) -> None:
        metas = await self._store.get_product_meta([v.product_id for v in views])
        by_category: dict[str, float] = defaultdict(float)
        by_universe: dict[str, float] = defaultdict(float)
        for pid, meta in metas.items():
            by_category[meta.category] += weights[pid]
            by_universe[meta.universe] += weights[pid]

        for affinities, weight, field in ((by_universe, W_UNIVERSE, "universe"), (by_category, W_CATEGORY, "category")):
            total = sum(affinities.values()) or 1.0
            for value, aff in sorted(affinities.items(), key=lambda kv: -kv[1])[:TOP_AFFINITIES]:
                await self._add_bucket_scores(scores, weight * aff / total, **{field: value})

    async def _add_bucket_scores(
        self, scores: dict[str, float], weight: float, category: str | None = None, universe: str | None = None
    ) -> None:
        bucket = await self._store.top_popular(NEIGHBOURS_PER_PRODUCT, category=category, universe=universe)
        if not bucket:
            return
        top = bucket[0][1]
        for pid, popularity in bucket:
            # +1 smoothing: a known but never viewed product still belongs to the bucket.
            scores[pid] += weight * (popularity + 1.0) / (top + 1.0)

    async def _popular(self, k: int, exclude: set[str]) -> list[str]:
        rows = await self._store.top_popular(k + len(exclude))
        return [pid for pid, _ in rows if pid not in exclude][:k]

    async def _fill(self, picked: list[str], k: int, exclude: set[str]) -> list[str]:
        if len(picked) >= k:
            return picked
        extra = await self._popular(k, exclude=exclude | set(picked))
        return (picked + extra)[:k]
