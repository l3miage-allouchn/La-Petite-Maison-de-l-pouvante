"""Prometheus metrics (exposed on /metrics)."""

from prometheus_client import Counter, Gauge, Histogram

EVENTS_CONSUMED = Counter(
    "reco_events_consumed_total",
    "product-viewed events handled by the consumer",
    ["outcome"],  # processed | duplicate | dlq
)
EVENT_PROCESSING = Histogram(
    "reco_event_processing_seconds",
    "Time to apply one event to the model",
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)
CONSUMER_ERRORS = Counter(
    "reco_consumer_errors_total",
    "Transient consumer errors (event retried, offset not committed)",
    ["kind"],
)
RECOMMENDATION_LATENCY = Histogram(
    "reco_recommendation_seconds",
    "Time to compute recommendations",
    ["endpoint"],  # user | similar
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)
CATALOG_PRODUCTS = Gauge("reco_catalog_products", "Products known from the last catalog sync")

HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"])
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.3, 0.5, 1.0, 2.5),
)
