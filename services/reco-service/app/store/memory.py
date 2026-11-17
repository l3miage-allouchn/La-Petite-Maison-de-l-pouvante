"""In-memory FeatureStore: same behaviour as Valkey, for unit tests and offline model experiments."""

from collections import defaultdict

from app.store.base import ProductMeta, View


def _ranked(scores: dict[str, float], limit: int) -> list[tuple[str, float]]:
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]


class MemoryFeatureStore:
    def __init__(self) -> None:
        self.seen_events: set[str] = set()
        self.meta: dict[str, ProductMeta] = {}
        self.views: dict[str, dict[str, float]] = defaultdict(dict)
        self.cooc: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.popular: dict[str, float] = {}
        self.popular_by_category: dict[str, dict[str, float]] = defaultdict(dict)
        self.popular_by_universe: dict[str, dict[str, float]] = defaultdict(dict)

    async def ping(self) -> bool:
        return True

    async def is_event_seen(self, event_id: str) -> bool:
        return event_id in self.seen_events

    async def mark_event_seen(self, event_id: str) -> None:
        self.seen_events.add(event_id)

    async def register_product(self, meta: ProductMeta) -> None:
        self.meta[meta.product_id] = meta
        self.popular.setdefault(meta.product_id, 0.0)
        self.popular_by_category[meta.category].setdefault(meta.product_id, 0.0)
        self.popular_by_universe[meta.universe].setdefault(meta.product_id, 0.0)

    async def get_product_meta(self, product_ids: list[str]) -> dict[str, ProductMeta]:
        return {pid: self.meta[pid] for pid in product_ids if pid in self.meta}

    async def add_view(self, viewer_key: str, product_id: str, timestamp: float, max_history: int) -> None:
        history = self.views[viewer_key]
        history[product_id] = max(timestamp, history.get(product_id, 0.0))
        if len(history) > max_history:
            for pid, _ in sorted(history.items(), key=lambda kv: kv[1])[: len(history) - max_history]:
                del history[pid]

    async def get_views(self, viewer_key: str, limit: int) -> list[View]:
        history = self.views.get(viewer_key, {})
        ordered = sorted(history.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
        return [View(pid, ts) for pid, ts in ordered]

    async def incr_cooccurrence(self, product_a: str, product_b: str, weight: float) -> None:
        self.cooc[product_a][product_b] += weight
        self.cooc[product_b][product_a] += weight

    async def get_cooccurrences(self, product_id: str, limit: int) -> list[tuple[str, float]]:
        return _ranked(dict(self.cooc.get(product_id, {})), limit)

    async def incr_popularity(self, meta: ProductMeta) -> None:
        self.meta.setdefault(meta.product_id, meta)
        for bucket in (
            self.popular,
            self.popular_by_category[meta.category],
            self.popular_by_universe[meta.universe],
        ):
            bucket[meta.product_id] = bucket.get(meta.product_id, 0.0) + 1.0

    async def top_popular(
        self, limit: int, category: str | None = None, universe: str | None = None
    ) -> list[tuple[str, float]]:
        if category is not None:
            return _ranked(self.popular_by_category.get(category, {}), limit)
        if universe is not None:
            return _ranked(self.popular_by_universe.get(universe, {}), limit)
        return _ranked(self.popular, limit)
