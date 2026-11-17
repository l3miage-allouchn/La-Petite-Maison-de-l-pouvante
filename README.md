# 🕯️ La Petite Maison de l'Épouvante

Plateforme e-commerce et communautaire (fictive) d'un éditeur de fanzine horreur/fantastique
possédant 4 magasins (Angoulême, Aix-en-Provence, Lyon, Londres), un festival et le collectif Evil Ed.

> Projet d'école — *Développement des applications logicielles*.
> Objectif : une **tranche verticale démontrable** qui traverse toute l'architecture et prouve nos choix DevSecOps.

## Le parcours démontré

> Un visiteur consulte un produit et reçoit des recommandations.

```
Next.js ──► catalog-service (Spring Boot) ──► PostgreSQL
   │                 │
   │                 └─ product-viewed ──► Kafka ──► reco-service (FastAPI) ──► Valkey
   └──────────── « Vous aimerez aussi » ◄──────────────────┘
Authentification : Keycloak (OIDC)
```

Hors périmètre (maquettes uniquement) : panier, paiement, troc, chat, liseuse, abonnements, back-office.

## Prérequis (partie A)

| Outil | Version testée | Installation (macOS) |
|---|---|---|
| Docker Desktop (Compose v2+) | 29.x | <https://www.docker.com/products/docker-desktop/> |
| Git | 2.50 | `xcode-select --install` |
| GitHub CLI | 2.104 | `brew install gh` |
| Java (LTS) | 25 | `brew install openjdk@25` |
| Node.js / npm | 22 LTS | `brew install node@22` |
| Python | 3.12+ | `brew install python` |
| uv | 0.13 | `brew install uv` |
| pre-commit / Gitleaks | 4.7 / 8.30 | `brew install pre-commit gitleaks` |

Docker Desktop : allouer **au moins 8 Go de RAM** (10 à 11 Go pour la partie Kubernetes).

> macOS : si `docker pull` échoue avec `docker-credential-desktop: executable file not found`,
> ajouter `export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"` à `~/.zshrc`.

## Démarrage rapide

```bash
git clone https://github.com/l3miage-allouchn/La-Petite-Maison-de-l-pouvante.git
cd La-Petite-Maison-de-l-pouvante
make bootstrap      # génère .env (secrets aléatoires) + installe les hooks pre-commit
make infra          # PostgreSQL, Kafka (+ topics), Valkey, Keycloak, Kafbat UI — attend que tout soit healthy
make kafka-demo-event   # publie un événement de test, visible dans Kafbat UI
make help           # liste des cibles
```

| Cible | Effet |
|---|---|
| `make infra` / `make infra-down` | Démarre / arrête l'infrastructure seule |
| `make dev` / `make dev-down` | Démarre / arrête toute l'application |
| `make dev-reset` | Arrête tout et **supprime les volumes** (realm réimporté, base vide) |
| `make status`, `make logs S=keycloak` | État des conteneurs, logs |

Tous les ports sont liés à `127.0.0.1` uniquement. Si un port est déjà pris sur votre machine,
changez-le dans `.env` (`POSTGRES_HOST_PORT`, `VALKEY_HOST_PORT`, …) : les conteneurs, eux, communiquent
par le réseau Docker `pme-net` et ne sont pas affectés.

## URLs (à partir de la phase 1)

| Service | Docker Compose | Kubernetes |
|---|---|---|
| Frontend | http://localhost:3000 | https://shop.localhost |
| catalog-service | http://localhost:8081 | https://shop.localhost/api/catalog |
| reco-service | http://localhost:8082 | https://shop.localhost/api/reco |
| Keycloak | http://localhost:8080 | https://auth.localhost |
| UI Kafka (Kafbat) | http://localhost:8085 | — |
| ArgoCD / Grafana | — | https://argocd.localhost / https://grafana.localhost |

Comptes de test (realm `petite-maison`) : `nesrine` (rôle `client`) et `admin` (rôle `admin`).
Les mots de passe sont dans votre `.env` (`grep KC_USER_ .env`).

- Console de compte utilisateur : <http://localhost:8080/realms/petite-maison/account>
- Console d'administration Keycloak : <http://localhost:8080/admin> (`KC_BOOTSTRAP_ADMIN_USERNAME` / `KC_BOOTSTRAP_ADMIN_PASSWORD`)
- Jeton de test en ligne de commande (client `dev-cli`, **local uniquement**) :

```bash
set -a; . ./.env; set +a
curl -s http://localhost:8080/realms/petite-maison/protocol/openid-connect/token \
  -d grant_type=password -d client_id=dev-cli -d username=nesrine \
  --data-urlencode "password=$KC_USER_NESRINE_PASSWORD" | jq -r .access_token
```

## catalog-service (phase 2)

Spring Boot 4.1 / Java 25, PostgreSQL (Flyway, 30 produits de démo), publication Kafka de `product-viewed`.

```bash
make test-catalog                     # tests unitaires + intégration Testcontainers + couverture ≥ 70 %
make dev                              # construit l'image et démarre toute la stack
curl -s "localhost:8081/api/catalog/products?category=FIGURINE&store=LYON&q=orc&page=0&size=12"
curl -s -H "X-Session-Id: session-demo-0001" localhost:8081/api/catalog/products/fig-orc-evil-ed
# → un événement apparaît dans Kafbat UI (topic catalog.product-viewed)
```

| Endpoint | Accès | Description |
|---|---|---|
| `GET /api/catalog/products?category=&q=&store=&page=&size=` | public | Liste paginée (`size` ≤ 50), triée par nom |
| `GET /api/catalog/products/{id}` | public (JWT optionnel) | Détail + événement `product-viewed` (clé = `sub` du JWT, sinon `X-Session-Id`) |
| `GET /actuator/health`, `/actuator/prometheus` | public | Santé (probes liveness/readiness), métriques (`products_viewed_total`…) |

- Erreurs au format **RFC 9457** (`application/problem+json`), sans fuite d'information interne.
- En-tête `X-Correlation-Id` accepté ou généré, renvoyé dans la réponse, présent dans les logs JSON et dans les headers Kafka.
- Contrat de l'événement : [docs/events/product-viewed.schema.json](docs/events/product-viewed.schema.json).

## Feuille de route

| Phase | Contenu | État |
|---|---|---|
| 0 | Initialisation, dépôt, pre-commit / Gitleaks | ✅ |
| 1 | Infra locale Docker Compose (Postgres, Kafka, Valkey, Keycloak) | ✅ |
| 2 | catalog-service (Spring Boot) | ✅ |
| 3 | reco-service (FastAPI) | ⏳ |
| 4 | Frontend (Next.js) | ⏳ |
| 5 | CI GitHub Actions (tests, Sonar, Trivy, SBOM, Cosign, ZAP) | ⏳ |
| 6 | Cluster Kind + plateforme GitOps (ArgoCD) | ⏳ |
| 7 | Déploiement des services + Kyverno | ⏳ |
| 8 | Observabilité (Grafana, Loki, alertes) | ⏳ |
| 9 | Démo Kafka vs RabbitMQ | ⏳ |
| 10 | Tests de charge k6 et documentation finale | ⏳ |

## Sécurité

- Aucun secret dans Git : `.env` local (ignoré), secrets GitHub en CI, Secrets Kubernetes créés par `make secrets`.
- Hook pre-commit **Gitleaks** : tout commit contenant un secret est bloqué.
- Dependabot, secret scanning et push protection activés sur le dépôt.

Voir [docs/DECISIONS.md](docs/DECISIONS.md) pour les choix d'architecture.

## Licence

[MIT](LICENSE)
