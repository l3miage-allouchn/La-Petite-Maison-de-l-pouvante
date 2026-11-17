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

## Démarrage rapide

```bash
git clone https://github.com/l3miage-allouchn/La-Petite-Maison-de-l-pouvante.git
cd La-Petite-Maison-de-l-pouvante
make bootstrap      # crée .env depuis .env.example + installe les hooks pre-commit
# éditer .env et remplacer toutes les valeurs "change-me"
make help           # liste des cibles
```

Les cibles `make infra`, `make dev`, etc. seront opérationnelles au fil des phases.

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
Les mots de passe sont définis dans votre `.env`.

## Feuille de route

| Phase | Contenu | État |
|---|---|---|
| 0 | Initialisation, dépôt, pre-commit / Gitleaks | ✅ |
| 1 | Infra locale Docker Compose (Postgres, Kafka, Valkey, Keycloak) | ⏳ |
| 2 | catalog-service (Spring Boot) | ⏳ |
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
