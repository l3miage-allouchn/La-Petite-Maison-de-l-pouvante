"""Feature store contract used by recommenders. Two implementations: Valkey (runtime) and memory (tests,
offline experiments). Keys for viewers are "u:<user_id>" (authenticated) or "s:<session_id>" (anonymous)."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProductMeta:
    product_id: str
    category: str
    universe: str


@dataclass(frozen=True, slots=True)
class View:
    product_id: str
    timestamp: float  # epoch seconds of the most recent view


class FeatureStore(Protocol):
    async def ping(self) -> bool: ...

    async def is_event_seen(self, event_id: str) -> bool:
        """True if this event id was already applied (idempotent consumption)."""
        ...

    async def mark_event_seen(self, event_id: str) -> None:
        """Called only after the event was applied successfully."""
        ...

    async def register_product(self, meta: ProductMeta) -> None:
        """Makes a product known (metadata + popularity 0) without counting a view."""
        ...

    async def get_product_meta(self, product_ids: list[str]) -> dict[str, ProductMeta]: ...

    async def add_view(self, viewer_key: str, product_id: str, timestamp: float, max_history: int) -> None: ...

    async def get_views(self, viewer_key: str, limit: int) -> list[View]:
        """Most recent first, one entry per product."""
        ...

    async def incr_cooccurrence(self, product_a: str, product_b: str, weight: float) -> None:
        """Symmetric: both a→b and b→a are incremented."""
        ...

    async def get_cooccurrences(self, product_id: str, limit: int) -> list[tuple[str, float]]: ...

    async def incr_popularity(self, meta: ProductMeta) -> None: ...

    async def top_popular(
        self, limit: int, category: str | None = None, universe: str | None = None
    ) -> list[tuple[str, float]]:
        """Highest score first; ties broken by product id for determinism."""
        ...
