"""Periodic import of the product catalog, so that never-viewed products can be recommended too."""

import asyncio
import logging

import httpx

from app.metrics import CATALOG_PRODUCTS
from app.store.base import FeatureStore, ProductMeta

log = logging.getLogger(__name__)

PAGE_SIZE = 50


async def sync_catalog(client: httpx.AsyncClient, base_url: str, store: FeatureStore) -> int:
    page, total_pages, count = 0, 1, 0
    while page < total_pages:
        response = await client.get(
            f"{base_url.rstrip('/')}/api/catalog/products", params={"page": page, "size": PAGE_SIZE}
        )
        response.raise_for_status()
        body = response.json()
        for product in body["content"]:
            await store.register_product(ProductMeta(product["id"], product["category"], product["universe"]))
            count += 1
        total_pages = int(body["totalPages"])
        page += 1
    CATALOG_PRODUCTS.set(count)
    return count


async def run_catalog_sync(base_url: str, store: FeatureStore, interval_seconds: int) -> None:
    """Never raises: the catalog is an enrichment, not a dependency for serving recommendations."""
    async with httpx.AsyncClient(timeout=5.0, headers={"X-Correlation-Id": "reco-catalog-sync"}) as client:
        while True:
            try:
                count = await sync_catalog(client, base_url, store)
                log.info("catalog synced products=%d", count)
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning("catalog sync failed (%s), retrying in 15s", exc)
                await asyncio.sleep(15)
