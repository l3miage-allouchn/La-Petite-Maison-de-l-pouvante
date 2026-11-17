from collections.abc import Callable, Iterator
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.model.cooccurrence import CooccurrenceRecommender
from app.store import MemoryFeatureStore
from tests.conftest import AUDIENCE, ISSUER


@pytest.fixture
def client(
    catalog_store: MemoryFeatureStore, recommender: CooccurrenceRecommender, rsa_key: rsa.RSAPrivateKey
) -> Iterator[TestClient]:
    settings = Settings(oidc_issuer_uri=ISSUER, oidc_audience=AUDIENCE, log_format="text")
    app = create_app(settings, store=catalog_store, recommender=recommender, start_background_tasks=False)
    with TestClient(app) as test_client:
        # Serve the test public key instead of calling Keycloak's JWKS endpoint.
        jwks = app.state.jwt_verifier._jwks
        jwks.get_signing_key_from_jwt = lambda _token: SimpleNamespace(key=rsa_key.public_key())
        yield test_client


def test_similar_is_public(client: TestClient) -> None:
    response = client.get("/api/reco/products/fig-nosferatu/similar", params={"limit": 3})
    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == "fig-nosferatu"
    assert body["model"] == "cooccurrence"
    assert len(body["items"]) == 3
    assert "fig-nosferatu" not in body["items"]


def test_recommendations_require_a_token(client: TestClient) -> None:
    response = client.get("/api/reco/recommendations/user-1")
    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["www-authenticate"] == "Bearer"


def test_recommendations_reject_forged_token(
    client: TestClient, make_token: Callable[..., str], other_rsa_key: rsa.RSAPrivateKey
) -> None:
    token = make_token(sub="user-1", key=other_rsa_key)
    response = client.get("/api/reco/recommendations/user-1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_user_cannot_read_someone_elses_recommendations(client: TestClient, make_token: Callable[..., str]) -> None:
    token = make_token(sub="user-2")
    response = client.get("/api/reco/recommendations/user-1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["title"] == "Forbidden"


def test_user_reads_own_recommendations(client: TestClient, make_token: Callable[..., str]) -> None:
    token = make_token(sub="user-1")
    response = client.get(
        "/api/reco/recommendations/user-1",
        params={"limit": 2},
        headers={"Authorization": f"Bearer {token}", "X-Correlation-Id": "corr-api-0001"},
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == "user-1"
    assert len(response.json()["items"]) == 2
    assert response.headers["x-correlation-id"] == "corr-api-0001"
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    "url",
    [
        "/api/reco/products/NOT_A_SLUG/similar",
        "/api/reco/products/fig-nosferatu/similar?limit=0",
        "/api/reco/products/fig-nosferatu/similar?limit=999",
    ],
)
def test_invalid_parameters_are_problem_details(client: TestClient, url: str) -> None:
    response = client.get(url)
    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["status"] == 400


def test_unknown_route_is_problem_detail(client: TestClient) -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json()["title"] == "Not found"


def test_health_and_metrics(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["components"] == {"valkey": "UP", "kafka_consumer": "DISABLED"}

    client.get("/api/reco/products/fig-nosferatu/similar")
    metrics = client.get("/metrics/").text
    assert "reco_recommendation_seconds_bucket" in metrics
    assert 'http_requests_total{method="GET",route="/api/reco/products/{product_id}/similar",status="200"}' in metrics


def test_health_reports_down_when_store_fails(client: TestClient, catalog_store: MemoryFeatureStore) -> None:
    async def broken_ping() -> bool:
        raise ConnectionError("valkey down")

    catalog_store.ping = broken_ping  # type: ignore[method-assign]
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "DOWN"


def test_cors_allows_frontend_only(client: TestClient) -> None:
    ok = client.options(
        "/api/reco/products/fig-nosferatu/similar",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    evil = client.options(
        "/api/reco/products/fig-nosferatu/similar",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in evil.headers
