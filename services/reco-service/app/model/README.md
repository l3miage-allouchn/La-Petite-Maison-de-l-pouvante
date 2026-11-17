# Le modèle de recommandation — guide pour la data scientist

Ce dossier est **ta zone**. Tu peux y remplacer complètement l'algorithme sans toucher au reste du service
(consommateur Kafka, API, sécurité, métriques). Le reste du code ne connaît qu'une seule chose : l'interface
`Recommender`.

```
services/reco-service/app/
├── model/                 ← ta zone
│   ├── base.py            ← l'interface à respecter (ne pas changer les signatures)
│   ├── cooccurrence.py    ← l'implémentation actuelle (référence à battre)
│   ├── __init__.py        ← le registre des modèles (RECO_MODEL)
│   ├── offline.py         ← bac à sable hors-ligne + évaluation
│   ├── demo_events.json   ← 177 événements de démo (personas + visiteurs anonymes)
│   └── demo_catalog.json  ← les 30 produits du catalogue
├── store/                 ← stockage des signaux (Valkey en vrai, mémoire en test)
├── consumer.py            ← lit Kafka et appelle model.update(event)
└── api/routes.py          ← appelle model.recommend() / model.similar()
```

## 1. L'interface à respecter

```python
class Recommender(ABC):
    name: str                                                   # ex. "cooccurrence"
    async def update(self, event: ProductViewedEvent) -> None   # appelé pour CHAQUE événement Kafka
    async def recommend(self, user_id: str, k: int) -> list[str] # k ids produits pour un utilisateur connecté
    async def similar(self, product_id: str, k: int) -> list[str] # « Vous aimerez aussi » (jamais product_id)
```

Règles du contrat :

| Règle | Pourquoi |
|---|---|
| `recommend()` renvoie des produits **même pour un utilisateur inconnu** (démarrage à froid → populaires) | la page d'accueil ne doit jamais être vide |
| `similar()` ne renvoie jamais le produit lui-même | bloc « Vous aimerez aussi » |
| Au plus `k` éléments, sans doublon, du meilleur au moins bon | l'API les affiche dans l'ordre |
| Rapide : objectif **< 50 ms** par appel (le p95 global de l'API doit rester < 300 ms) | mesuré par `reco_recommendation_seconds` dans Grafana |
| `update()` est appelé **une seule fois** par événement (dédoublonnage fait avant) | tu n'as pas à gérer les doublons Kafka |
| Les méthodes sont `async` | elles lisent Valkey sans bloquer le serveur ; si ton code est purement calcul (numpy…), c'est OK tant qu'il est rapide |

Un événement (`app/events.py`, contrat complet : `docs/events/product-viewed.schema.json`) :

```json
{ "event_id": "uuid", "event_type": "product.viewed", "occurred_at": "2026-11-17T13:51:09Z",
  "user_id": "uuid Keycloak ou null", "session_id": "session-…", "product_id": "fig-nosferatu",
  "category": "FIGURINE", "universe": "gothique", "source": "product_page" }
```

`event.viewer_key` vaut `u:<user_id>` pour un utilisateur connecté, `s:<session_id>` pour un visiteur anonyme.
Les visiteurs anonymes alimentent la co-occurrence ; `recommend()` n'est appelé que pour des utilisateurs connectés.

## 2. Le modèle actuel (la référence)

`cooccurrence.py`, volontairement simple et explicable :

- **Co-occurrence** : quand un visiteur voit B peu après A, la paire (A, B) gagne `decay(écart de temps)`.
- **Affinité** : les vues récentes d'un utilisateur donnent une distribution sur les catégories et les univers ;
  les produits populaires de ses catégories/univers préférés reçoivent un bonus.
- **Récence** : `decay(âge) = 0.5 ** (âge / demi-vie)`, demi-vie 72 h.
- **Démarrage à froid** : produits les plus vus.
- Les produits déjà vus par l'utilisateur sont exclus.

Score actuel sur les données de démo : **HitRate@4 = 0,50, MRR@4 = 0,21** (`make reco-offline ARGS="--evaluate"`).

## 3. Travailler seule, sans Docker

Prérequis : `brew install uv` (une fois), puis dans `services/reco-service/` :

```bash
uv sync                                                   # installe les dépendances (crée .venv)
uv run python -m app.model.offline                        # recommandations pour chaque persona
uv run python -m app.model.offline --user u-orc-fan --k 6
uv run python -m app.model.offline --similar fig-nosferatu
uv run python -m app.model.offline --evaluate             # HitRate@k et MRR@k
uv run python -m app.model.offline --model mon-modele --evaluate
uv run pytest tests/unit -q                               # tests unitaires (dont ceux du modèle)
```

Le bac à sable rejoue `demo_events.json` dans un stockage **en mémoire** (`MemoryFeatureStore`), qui se comporte
exactement comme Valkey. L'évaluation utilise le protocole *next-new-item* : pour chaque utilisateur, on cache le
dernier produit qu'il a découvert (et tout ce qu'il a fait ensuite), on entraîne sur le reste, puis on regarde si ce
produit est dans les `k` recommandations.

Tu peux utiliser tes propres événements : `--events mon_fichier.json` (une liste JSON d'événements).

## 4. Brancher ton propre modèle

1. Crée `app/model/mon_modele.py` :

   ```python
   from app.events import ProductViewedEvent, user_key
   from app.model.base import Recommender
   from app.store.base import FeatureStore


   class MonModele(Recommender):
       name = "mon-modele"

       def __init__(self, store: FeatureStore) -> None:
           self._store = store

       async def update(
           self, event: ProductViewedEvent
       ) -> None: ...  # mettre à jour tes signaux (tu peux réutiliser le store, cf. ci-dessous)

       async def recommend(self, user_id: str, k: int) -> list[str]: ...

       async def similar(self, product_id: str, k: int) -> list[str]: ...
   ```

2. Déclare-le dans `app/model/__init__.py` :

   ```python
   _REGISTRY = {"cooccurrence": CooccurrenceRecommender, "mon-modele": MonModele}
   ```

3. Teste-le hors-ligne : `uv run python -m app.model.offline --model mon-modele --evaluate`.
4. Active-le dans la stack : `RECO_MODEL=mon-modele` dans `.env`, puis `make dev`.

Le `FeatureStore` (`app/store/base.py`) te donne gratuitement : métadonnées produit (catégorie, univers) de **tout**
le catalogue (synchronisé depuis catalog-service), historique récent par visiteur, co-occurrences pondérées,
popularité globale / par catégorie / par univers. Si ton modèle a besoin d'autres signaux, ajoute une méthode au
`FeatureStore` (et à ses deux implémentations) ou demande-moi.

Pour un modèle entraîné hors-ligne (factorisation de matrice, embeddings…) : entraîne-le à partir des événements
(fichier JSON ou export Kafka), sauvegarde-le dans un fichier du dossier `model/`, charge-le dans `__init__`, et
garde `update()` pour les signaux temps réel.

## 5. Récupérer les vrais événements et réentraîner

Kafka **conserve** les événements (contrairement à une file classique) : on peut tout relire depuis le début.

**Exporter les événements de la stack locale en JSON** (pour le bac à sable) :

```bash
docker compose exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic catalog.product-viewed \
  --from-beginning --timeout-ms 5000 2>/dev/null \
  | python3 -c "import sys, json; print(json.dumps([json.loads(l) for l in sys.stdin if l.strip()]))" \
  > services/reco-service/my_events.json
uv run python -m app.model.offline --events my_events.json --evaluate
```

**Rejouer tout l'historique dans le service** (après un changement de modèle) :

```bash
make reco-replay
```

Ce que fait la commande (`scripts/reco-replay.sh`) : arrêt de reco-service → suppression des clés `reco:*` dans
Valkey → remise à zéro des offsets du groupe de consommateurs `reco-service`
(`kafka-consumer-groups.sh --reset-offsets --to-earliest --execute`) → redémarrage : chaque événement est
relu et repasse dans `update()`.

Pour voir le consommateur en direct : <http://localhost:8085> → *Consumers* → `reco-service` (offsets et lag).

## 6. Avant de pousser

```bash
make test-reco     # ruff + mypy + pytest + couverture ≥ 70 % (la CI exécutera la même chose)
```
