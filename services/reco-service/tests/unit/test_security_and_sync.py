import time
from collections.abc import Callable
from types import SimpleNamespace

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.catalog_sync import sync_catalog
from app.security import InvalidTokenError, JwtVerifier
from app.store import MemoryFeatureStore
from tests.conftest import AUDIENCE, ISSUER


@pytest.fixture
def verifier(rsa_key: rsa.RSAPrivateKey) -> JwtVerifier:
    v = JwtVerifier(ISSUER, AUDIENCE, "http://keycloak.invalid/certs")
    v._jwks.get_signing_key_from_jwt = lambda _token: SimpleNamespace(key=rsa_key.public_key())  # type: ignore[method-assign]
    return v


async def test_valid_token_gives_principal_with_realm_roles(
    verifier: JwtVerifier, make_token: Callable[..., str]
) -> None:
    principal = await verifier.verify(make_token(sub="abc", realm_access={"roles": ["client", "admin"]}))
    assert principal.subject == "abc"
    assert principal.username == "nesrine"
    assert principal.roles == {"client", "admin"}


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": int(time.time()) - 3600},  # expired
        {"aud": "another-api"},  # wrong audience
        {"iss": "https://evil.example/realms/x"},  # wrong issuer
    ],
)
async def test_invalid_tokens_are_rejected(
    verifier: JwtVerifier, make_token: Callable[..., str], claims: dict[str, object]
) -> None:
    with pytest.raises(InvalidTokenError):
        await verifier.verify(make_token(**claims))


async def test_garbage_token_is_rejected() -> None:
    verifier = JwtVerifier(ISSUER, AUDIENCE, "http://keycloak.invalid/certs")
    with pytest.raises(InvalidTokenError):
        await verifier.verify("not-a-jwt")


async def test_catalog_sync_registers_every_page(store: MemoryFeatureStore) -> None:
    pages = {
        "0": {"content": [{"id": "p1", "category": "BD", "universe": "giallo"}], "totalPages": 2},
        "1": {"content": [{"id": "p2", "category": "FIGURINE", "universe": "slasher"}], "totalPages": 2},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/catalog/products"
        return httpx.Response(200, json=pages[request.url.params["page"]])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        count = await sync_catalog(client, "http://catalog/", store)

    assert count == 2
    assert set(store.meta) == {"p1", "p2"}
    assert await store.top_popular(5, universe="slasher") == [("p2", 0.0)]
