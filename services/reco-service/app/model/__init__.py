"""Model registry. To plug a new model: implement `Recommender`, add it to `_REGISTRY`,
then select it with the RECO_MODEL environment variable. Nothing else needs to change."""

from collections.abc import Callable

from app.model.base import Recommender
from app.model.cooccurrence import CooccurrenceRecommender
from app.store.base import FeatureStore

_REGISTRY: dict[str, Callable[[FeatureStore], Recommender]] = {
    "cooccurrence": CooccurrenceRecommender,
}


def build_recommender(name: str, store: FeatureStore) -> Recommender:
    try:
        factory = _REGISTRY[name]
    except KeyError:
        raise ValueError(f"Unknown RECO_MODEL '{name}'. Available: {sorted(_REGISTRY)}") from None
    return factory(store)


__all__ = ["Recommender", "build_recommender"]
