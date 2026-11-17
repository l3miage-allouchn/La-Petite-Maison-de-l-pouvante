"""Valkey-backed FeatureStore.

Key layout (prefix "reco:" by default):
  event:<event_id>              STRING  dedup marker, TTL 24 h
  product:<product_id>          HASH    category, universe
  views:<viewer_key>            ZSET    product_id -> last view epoch (trimmed to max_history, TTL 30 d)
  cooc:<product_id>             ZSET    product_id -> co-occurrence weight (recency weighted)
  popular                       ZSET    product_id -> view count
  popular:category:<category>   ZSET    idem, per category
  popular:universe:<universe>   ZSET    idem, per universe
"""

from valkey.asyncio import Valkey

from app.store.base import ProductMeta, View

EVENT_TTL_SECONDS = 24 * 3600
VIEWS_TTL_SECONDS = 30 * 24 * 3600


def _ranked(rows: list[tuple[str, float]], limit: int) -> list[tuple[str, float]]:
    # ZREVRANGE breaks ties by reverse lexicographic order; re-sort for a stable, documented order.
    return sorted(((str(m), float(s)) for m, s in rows), key=lambda kv: (-kv[1], kv[0]))[:limit]


class ValkeyFeatureStore:
    def __init__(self, client: Valkey, prefix: str = "reco:") -> None:
        self._r = client
        self._p = prefix

    def _k(self, *parts: str) -> str:
        return self._p + ":".join(parts)

    async def ping(self) -> bool:
        return bool(await self._r.ping())

    async def is_event_seen(self, event_id: str) -> bool:
        return bool(await self._r.exists(self._k("event", event_id)))

    async def mark_event_seen(self, event_id: str) -> None:
        await self._r.set(self._k("event", event_id), "1", ex=EVENT_TTL_SECONDS)

    async def register_product(self, meta: ProductMeta) -> None:
        async with self._r.pipeline(transaction=False) as pipe:
            pipe.hset(
                self._k("product", meta.product_id), mapping={"category": meta.category, "universe": meta.universe}
            )
            pipe.zadd(self._k("popular"), {meta.product_id: 0}, nx=True)
            pipe.zadd(self._k("popular", "category", meta.category), {meta.product_id: 0}, nx=True)
            pipe.zadd(self._k("popular", "universe", meta.universe), {meta.product_id: 0}, nx=True)
            await pipe.execute()

    async def get_product_meta(self, product_ids: list[str]) -> dict[str, ProductMeta]:
        if not product_ids:
            return {}
        async with self._r.pipeline(transaction=False) as pipe:
            for pid in product_ids:
                pipe.hgetall(self._k("product", pid))
            rows: list[dict[str, str]] = await pipe.execute()
        return {
            pid: ProductMeta(pid, row["category"], row["universe"])
            for pid, row in zip(product_ids, rows, strict=True)
            if row and "category" in row and "universe" in row
        }

    async def add_view(self, viewer_key: str, product_id: str, timestamp: float, max_history: int) -> None:
        key = self._k("views", viewer_key)
        async with self._r.pipeline(transaction=True) as pipe:
            pipe.zadd(key, {product_id: timestamp}, gt=True)  # keep the most recent timestamp
            pipe.zremrangebyrank(key, 0, -(max_history + 1))
            pipe.expire(key, VIEWS_TTL_SECONDS)
            await pipe.execute()

    async def get_views(self, viewer_key: str, limit: int) -> list[View]:
        rows = await self._r.zrevrange(self._k("views", viewer_key), 0, limit - 1, withscores=True)
        return [View(str(pid), float(ts)) for pid, ts in rows]

    async def incr_cooccurrence(self, product_a: str, product_b: str, weight: float) -> None:
        async with self._r.pipeline(transaction=False) as pipe:
            pipe.zincrby(self._k("cooc", product_a), weight, product_b)
            pipe.zincrby(self._k("cooc", product_b), weight, product_a)
            await pipe.execute()

    async def get_cooccurrences(self, product_id: str, limit: int) -> list[tuple[str, float]]:
        rows = await self._r.zrevrange(self._k("cooc", product_id), 0, limit * 2 - 1, withscores=True)
        return _ranked(rows, limit)

    async def incr_popularity(self, meta: ProductMeta) -> None:
        async with self._r.pipeline(transaction=False) as pipe:
            pipe.hsetnx(self._k("product", meta.product_id), "category", meta.category)
            pipe.hsetnx(self._k("product", meta.product_id), "universe", meta.universe)
            pipe.zincrby(self._k("popular"), 1, meta.product_id)
            pipe.zincrby(self._k("popular", "category", meta.category), 1, meta.product_id)
            pipe.zincrby(self._k("popular", "universe", meta.universe), 1, meta.product_id)
            await pipe.execute()

    async def top_popular(
        self, limit: int, category: str | None = None, universe: str | None = None
    ) -> list[tuple[str, float]]:
        if category is not None:
            key = self._k("popular", "category", category)
        elif universe is not None:
            key = self._k("popular", "universe", universe)
        else:
            key = self._k("popular")
        # Fetch a little more than needed so that ties are re-sorted deterministically.
        rows = await self._r.zrevrange(key, 0, limit * 2 - 1, withscores=True)
        return _ranked(rows, limit)
