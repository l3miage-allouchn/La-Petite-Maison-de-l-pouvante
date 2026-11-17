"""Shared fixtures: in-memory store, deterministic recommender, signed test JWTs."""

import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.events import ProductViewedEvent
from app.model.cooccurrence import CooccurrenceRecommender
from app.store import MemoryFeatureStore, ProductMeta

ISSUER = "http://localhost:8080/realms/petite-maison"
AUDIENCE = "catalog-api"
NOW = 1_800_000_000.0  # fixed "now" for recency computations

CATALOG = [
    ProductMeta("fig-orc-evil-ed", "FIGURINE", "heroic-fantasy"),
    ProductMeta("fig-orc-chaman-evil-ed", "FIGURINE", "heroic-fantasy"),
    ProductMeta("fig-nosferatu", "FIGURINE", "gothique"),
    ProductMeta("fig-masque-hockey", "FIGURINE", "slasher"),
    ProductMeta("fig-cthulhu-reveil", "FIGURINE", "lovecraftien"),
    ProductMeta("bd-orc-tome1", "BD", "heroic-fantasy"),
    ProductMeta("bluray-suspiria-4k", "BLURAY", "giallo"),
    ProductMeta("bluray-nosferatu-1922", "BLURAY", "gothique"),
    ProductMeta("fanzine-38-giallo", "FANZINE", "giallo"),
]
META = {m.product_id: m for m in CATALOG}


def make_event(
    product_id: str,
    user_id: str | None = "user-1",
    session_id: str = "session-0001",
    ts: float = NOW,
    **overrides: Any,
) -> ProductViewedEvent:
    meta = META[product_id]
    data: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "event_type": "product.viewed",
        "occurred_at": datetime.fromtimestamp(ts, UTC).isoformat(),
        "user_id": user_id,
        "session_id": session_id,
        "product_id": product_id,
        "category": meta.category,
        "universe": meta.universe,
        "source": "product_page",
    }
    data.update(overrides)
    return ProductViewedEvent.model_validate(data)


@pytest.fixture
def store() -> MemoryFeatureStore:
    return MemoryFeatureStore()


@pytest.fixture
async def catalog_store(store: MemoryFeatureStore) -> MemoryFeatureStore:
    for meta in CATALOG:
        await store.register_product(meta)
    return store


@pytest.fixture
def recommender(catalog_store: MemoryFeatureStore) -> CooccurrenceRecommender:
    return CooccurrenceRecommender(catalog_store, half_life_hours=72, history_size=20, clock=lambda: NOW)


# ---------------------------------------------------------------- JWT helpers
@pytest.fixture(scope="session")
def rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def other_rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def make_token(rsa_key: rsa.RSAPrivateKey) -> Callable[..., str]:
    def _make(sub: str = "user-1", key: rsa.RSAPrivateKey | None = None, **claims: Any) -> str:
        now = int(time.time())
        payload: dict[str, Any] = {
            "iss": ISSUER,
            "aud": [AUDIENCE, "account"],
            "sub": sub,
            "iat": now,
            "exp": now + 300,
            "preferred_username": "nesrine",
            "realm_access": {"roles": ["client"]},
        }
        payload.update(claims)
        return jwt.encode(payload, key or rsa_key, algorithm="RS256", headers={"kid": "test-key"})

    return _make
