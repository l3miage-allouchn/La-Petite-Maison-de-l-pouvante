"""Offline playground for the model — no Kafka, no Valkey, no Docker needed.

    uv run python -m app.model.offline                         # demo data, all users
    uv run python -m app.model.offline --user u-orc-fan --k 6
    uv run python -m app.model.offline --similar fig-nosferatu
    uv run python -m app.model.offline --evaluate              # leave-last-out HitRate@k / MRR
    uv run python -m app.model.offline --events my_events.json # any JSON list of product-viewed events

Events can be exported from Kafka (see app/model/README.md).
"""

import argparse
import asyncio
import json
from collections import defaultdict
from pathlib import Path

from app.events import ProductViewedEvent
from app.model import build_recommender
from app.model.base import Recommender
from app.store import MemoryFeatureStore, ProductMeta

HERE = Path(__file__).parent
DEFAULT_EVENTS = HERE / "demo_events.json"
DEFAULT_CATALOG = HERE / "demo_catalog.json"


def load_events(path: Path) -> list[ProductViewedEvent]:
    events = [ProductViewedEvent.model_validate(raw) for raw in json.loads(path.read_text(encoding="utf-8"))]
    return sorted(events, key=lambda e: e.occurred_at)


def load_catalog(path: Path | None) -> list[ProductMeta]:
    if path is None or not path.is_file():
        return []
    return [ProductMeta(p["id"], p["category"], p["universe"]) for p in json.loads(path.read_text(encoding="utf-8"))]


async def build(model: str, events: list[ProductViewedEvent], catalog: Path | None) -> Recommender:
    store = MemoryFeatureStore()
    for meta in load_catalog(catalog):
        await store.register_product(meta)
    recommender = build_recommender(model, store)
    # Recency is computed relative to "now": pin it to the last event so results are reproducible.
    if events and hasattr(recommender, "_clock"):
        last = events[-1].timestamp
        recommender._clock = lambda: last
    for event in events:
        if not await store.is_event_seen(str(event.event_id)):
            await recommender.update(event)
            await store.mark_event_seen(str(event.event_id))
    return recommender


async def evaluate(model: str, events: list[ProductViewedEvent], catalog: Path | None, k: int) -> None:
    """Next-new-item protocol: for each user, hide the last view of a product they had never seen before
    (and everything that user did afterwards), train on the rest, then check whether it is recommended."""
    last_by_user: dict[str, ProductViewedEvent] = {}
    seen: dict[str, set[str]] = defaultdict(set)
    for e in events:
        if e.user_id:
            if e.product_id not in seen[e.user_id]:
                last_by_user[e.user_id] = e
            seen[e.user_id].add(e.product_id)
    cutoff = {user: e.occurred_at for user, e in last_by_user.items()}
    train = [e for e in events if not (e.user_id in cutoff and e.occurred_at >= cutoff[e.user_id])]
    recommender = await build(model, train, catalog)

    hits, reciprocal_ranks = 0, 0.0
    for user, target in sorted(last_by_user.items()):
        items = await recommender.recommend(user, k)
        rank = items.index(target.product_id) + 1 if target.product_id in items else None
        hits += rank is not None
        reciprocal_ranks += 1 / rank if rank else 0.0
        print(f"  {user:18} target={target.product_id:28} rank={rank}")
    n = len(last_by_user) or 1
    print(f"\nHitRate@{k} = {hits / n:.2f}   MRR@{k} = {reciprocal_ranks / n:.2f}   (users={n})")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--events", type=Path, default=DEFAULT_EVENTS)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--model", default="cooccurrence")
    parser.add_argument("--user", help="only this user")
    parser.add_argument("--similar", metavar="PRODUCT_ID", help="show products similar to this one")
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args()

    events = load_events(args.events)
    print(f"{len(events)} events loaded from {args.events}")
    if args.evaluate:
        await evaluate(args.model, events, args.catalog, args.k)
        return

    recommender = await build(args.model, events, args.catalog)
    if args.similar:
        print(f"\nsimilar({args.similar}) = {await recommender.similar(args.similar, args.k)}")
        return

    history: dict[str, list[str]] = defaultdict(list)
    for e in events:
        if e.user_id:
            history[e.user_id].append(e.product_id)
    users = [args.user] if args.user else sorted(history)
    for user in users:
        print(f"\n{user}  (last views: {history.get(user, [])[-5:]})")
        print(f"  recommend -> {await recommender.recommend(user, args.k)}")
    print(f"\ncold start (unknown user) -> {await recommender.recommend('nobody', args.k)}")


if __name__ == "__main__":
    asyncio.run(main())
