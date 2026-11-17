"""The ONLY contract between the model and the rest of the service.

The Kafka consumer calls `update()` once per (deduplicated, validated) event.
The HTTP API calls `recommend()` and `similar()`.
Nothing else in the service knows how recommendations are computed.
"""

from abc import ABC, abstractmethod

from app.events import ProductViewedEvent


class Recommender(ABC):
    #: Short name, exposed in API responses and metrics (e.g. "cooccurrence").
    name: str = "base"

    @abstractmethod
    async def update(self, event: ProductViewedEvent) -> None:
        """Learns from one product view (anonymous or authenticated)."""

    @abstractmethod
    async def recommend(self, user_id: str, k: int) -> list[str]:
        """Up to k product ids for an authenticated user, best first.
        Must return popular products for a user without history (cold start)."""

    @abstractmethod
    async def similar(self, product_id: str, k: int) -> list[str]:
        """Up to k product ids related to product_id ("Vous aimerez aussi"), never product_id itself."""
