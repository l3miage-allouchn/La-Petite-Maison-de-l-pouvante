"""HTTP API. Errors are RFC 9457 problem details (see app.main)."""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.events import PRODUCT_ID_PATTERN, USER_ID_PATTERN
from app.metrics import RECOMMENDATION_LATENCY
from app.model.base import Recommender
from app.security import InvalidTokenError, JwtVerifier, Principal
from app.store.base import FeatureStore

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)

Limit = Annotated[int, Query(ge=1, le=20, description="Number of products")]


class RecommendationResponse(BaseModel):
    user_id: str
    model: str
    items: list[str]


class SimilarResponse(BaseModel):
    product_id: str
    model: str
    items: list[str]


def get_recommender(request: Request) -> Recommender:
    recommender: Recommender = request.app.state.recommender
    return recommender


def get_store(request: Request) -> FeatureStore:
    store: FeatureStore = request.app.state.store
    return store


async def current_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Bearer token required", headers={"WWW-Authenticate": "Bearer"}
        )
    verifier: JwtVerifier = request.app.state.jwt_verifier
    try:
        return await verifier.verify(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        ) from None


@router.get("/api/reco/recommendations/{user_id}", response_model=RecommendationResponse)
async def recommendations(
    user_id: Annotated[str, Path(pattern=USER_ID_PATTERN)],
    principal: Annotated[Principal, Depends(current_principal)],
    recommender: Annotated[Recommender, Depends(get_recommender)],
    limit: Limit = 4,
) -> RecommendationResponse:
    # Object-level authorization: a user only reads their own recommendations (no IDOR).
    if principal.subject != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only read your own recommendations")
    with RECOMMENDATION_LATENCY.labels("user").time():
        items = await recommender.recommend(user_id, limit)
    return RecommendationResponse(user_id=user_id, model=recommender.name, items=items)


@router.get("/api/reco/products/{product_id}/similar", response_model=SimilarResponse)
async def similar(
    product_id: Annotated[str, Path(pattern=PRODUCT_ID_PATTERN)],
    recommender: Annotated[Recommender, Depends(get_recommender)],
    limit: Limit = 4,
) -> SimilarResponse:
    with RECOMMENDATION_LATENCY.labels("similar").time():
        items = await recommender.similar(product_id, limit)
    return SimilarResponse(product_id=product_id, model=recommender.name, items=items)


@router.get("/health", include_in_schema=False)
async def health(request: Request, store: Annotated[FeatureStore, Depends(get_store)]) -> JSONResponse:
    started = time.perf_counter()
    try:
        valkey_up = await store.ping()
    except Exception:
        valkey_up = False
    consumer = request.app.state.consumer
    consumer_state = "DISABLED" if consumer is None else ("UP" if consumer.running else "STARTING")
    body = {
        "status": "UP" if valkey_up else "DOWN",
        "components": {"valkey": "UP" if valkey_up else "DOWN", "kafka_consumer": consumer_state},
        "check_ms": round((time.perf_counter() - started) * 1000, 1),
    }
    return JSONResponse(body, status_code=200 if valkey_up else 503)
