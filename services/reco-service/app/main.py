"""FastAPI application: HTTP API + Kafka consumer + catalog sync, in a single process.

Run with: uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8080
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from starlette.exceptions import HTTPException
from valkey.asyncio import Valkey

from app.api.routes import router
from app.catalog_sync import run_catalog_sync
from app.config import Settings, get_settings
from app.consumer import EventConsumer
from app.logging_setup import configure_logging, correlation_id_var, sanitize_correlation_id
from app.metrics import HTTP_LATENCY, HTTP_REQUESTS
from app.model import build_recommender
from app.model.base import Recommender
from app.security import JwtVerifier
from app.store.base import FeatureStore
from app.store.valkey_store import ValkeyFeatureStore

log = logging.getLogger("app")

CORRELATION_HEADER = "X-Correlation-Id"
_QUIET_PATHS = {"/health", "/metrics", "/metrics/"}


def _problem(status: int, title: str, detail: str, instance: str) -> JSONResponse:
    return JSONResponse(
        {"type": "about:blank", "title": title, "status": status, "detail": detail, "instance": instance},
        status_code=status,
        media_type="application/problem+json",
    )


def create_app(
    settings: Settings | None = None,
    store: FeatureStore | None = None,
    recommender: Recommender | None = None,
    start_background_tasks: bool = True,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client: Valkey | None = None
        active_store = store
        if active_store is None:
            password = settings.valkey_password.get_secret_value() if settings.valkey_password else None
            client = Valkey(
                host=settings.valkey_host,
                port=settings.valkey_port,
                password=password,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2,
                health_check_interval=30,
            )
            active_store = ValkeyFeatureStore(client, settings.valkey_key_prefix)
        app.state.store = active_store
        app.state.recommender = recommender or build_recommender(settings.reco_model, active_store)
        app.state.jwt_verifier = JwtVerifier(
            settings.oidc_issuer_uri, settings.oidc_audience, settings.oidc_jwk_set_uri
        )
        app.state.consumer = None
        tasks: list[asyncio.Task[None]] = []

        if start_background_tasks and settings.consumer_enabled:
            app.state.consumer = EventConsumer(settings, app.state.recommender, active_store)
            await app.state.consumer.start()
        if start_background_tasks and settings.catalog_api_url:
            tasks.append(
                asyncio.create_task(
                    run_catalog_sync(settings.catalog_api_url, active_store, settings.catalog_sync_interval_seconds)
                )
            )
        log.info("reco-service started model=%s", app.state.recommender.name)
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            if app.state.consumer is not None:
                await app.state.consumer.stop()
            if client is not None:
                await client.aclose()

    app = FastAPI(
        title="reco-service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/reco/docs",
        openapi_url="/api/reco/openapi.json",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_methods=["GET"],
        allow_headers=["Authorization", "Content-Type", CORRELATION_HEADER],
        expose_headers=[CORRELATION_HEADER],
        max_age=3600,
    )

    @app.middleware("http")
    async def observe(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        correlation_id = sanitize_correlation_id(request.headers.get(CORRELATION_HEADER))
        token = correlation_id_var.set(correlation_id)
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers[CORRELATION_HEADER] = correlation_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Cache-Control"] = "no-store"
            return response
        finally:
            elapsed = time.perf_counter() - started
            # Route template (set by the router once matched) keeps metric cardinality low.
            matched = request.scope.get("route")
            route = getattr(matched, "path", None) or (
                "/metrics" if request.url.path.startswith("/metrics") else "unmatched"
            )
            HTTP_REQUESTS.labels(request.method, route, str(status)).inc()
            HTTP_LATENCY.labels(request.method, route).observe(elapsed)
            if request.url.path not in _QUIET_PATHS:
                log.info("%s %s %d %.1fms", request.method, route, status, elapsed * 1000)
            correlation_id_var.reset(token)

    @app.exception_handler(HTTPException)
    async def http_problem(request: Request, exc: HTTPException) -> JSONResponse:
        response = _problem(exc.status_code, _title(exc.status_code), str(exc.detail), request.url.path)
        for key, value in (exc.headers or {}).items():
            response.headers[key] = value
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_problem(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = ", ".join(".".join(str(p) for p in err["loc"]) for err in exc.errors())
        return _problem(400, "Invalid request", f"Invalid parameter(s): {fields}", request.url.path)

    @app.exception_handler(Exception)
    async def unexpected_problem(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unexpected error")
        return _problem(500, "Internal error", "An unexpected error occurred.", request.url.path)

    app.include_router(router)
    app.mount("/metrics", make_asgi_app())
    return app


def _title(status: int) -> str:
    return {400: "Invalid request", 401: "Unauthorized", 403: "Forbidden", 404: "Not found"}.get(status, "Error")
