# CLAUDE.md — mémoire du projet

Projet d'école « La Petite Maison de l'Épouvante » : tranche verticale e-commerce
(consultation produit → événement Kafka → recommandations) démontrant une chaîne DevSecOps complète.
Dépôt : https://github.com/l3miage-allouchn/La-Petite-Maison-de-l-pouvante (public, branche `main`).

## Équipe
- Propriétaire du dépôt : DevOps / Kubernetes.
- Binôme : data scientist, propriétaire de `services/reco-service/app/model/` (ne pas modifier sans raison ; respecter l'interface `recommend(user_id, k)` / `similar(product_id, k)`).

## Méthode
- Travail **phase par phase** (voir README). En fin de phase : bilan, commandes de vérification, push, **attendre validation**.
- Partie A (phases 0-5) = Docker Compose ; partie B (6-10) = Kubernetes. Aucun manifest K8s avant la phase 6.
- Mettre à jour ce fichier et `docs/DECISIONS.md` (ADR) à chaque décision.

## Conventions
- Code, identifiants, commits : **anglais**. Docs (README, docs/) : **français**.
- Commits : Conventional Commits (`feat:`, `fix:`, `ci:`, `chore:`, `docs:`, `test:`), petits et fréquents.
- Images de base officielles avec tag précis, jamais `latest`. Conteneurs **non root**.
- GitHub Actions épinglées par **SHA complet** + version en commentaire.
- Interdits : Helm/images Bitnami, ingress-nginx, Secret K8s commité, conteneurs root.
- Requests/limits partout ; 1 réplique Kafka/Keycloak/PostgreSQL ; heaps JVM bornés (budget 16 Go).

## Secrets
- Local : `.env` (ignoré) ← `.env.example` (commité, valeurs `change-me`).
- CI : secrets GitHub. Cluster : `make secrets` (kubectl create secret --from-env-file, dry-run | apply). Jamais dans Git.

## Environnement du poste
- macOS Apple Silicon (arm64), 16 Go, Docker Desktop → images **multi-arch** (amd64 + arm64).
- Java : Homebrew par défaut = 27 (non LTS). Utiliser Java 25 :
  `export JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home`

## Commandes
```bash
make help          # liste des cibles
make bootstrap     # .env + pre-commit install
pre-commit run --all-files
gitleaks git -v    # scan de tout l'historique
```

## Choix déjà actés
Voir `docs/DECISIONS.md` (ADR-001 à ADR-005).
