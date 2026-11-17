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
  Aucune mention de Claude (pas de trailer `Co-Authored-By`, pas de « Generated with Claude Code » dans les PR).
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
make bootstrap     # .env (secrets aléatoires via scripts/gen-env.sh) + pre-commit install
make infra         # infra Compose (attend healthy) ; make dev-reset pour repartir de zéro
make kafka-demo-event
pre-commit run --all-files
gitleaks git -v    # scan de tout l'historique
```

## Infra locale (phase 1)
- Images : postgres:18.7-alpine, apache/kafka:4.4.0, valkey/valkey:9.1.3-alpine,
  quay.io/keycloak/keycloak:26.8.2, ghcr.io/kafbat/kafka-ui:v1.5.0.
- Réseau `pme-net`. Kafka : listener interne `kafka:19092`, externe `localhost:${KAFKA_HOST_PORT}`.
- Keycloak : issuer `http://localhost:8080/realms/petite-maison` ; depuis les conteneurs, JWKS via
  `http://keycloak:8080/realms/petite-maison/protocol/openid-connect/certs` (backchannel dynamique).
- Realm importé seulement si absent : après modification du JSON → `make dev-reset`.
- Placeholders `${VAR}` dans le realm, résolus depuis l'environnement du conteneur Keycloak.
- Poste de dev : 5432 et 6379 déjà pris → `.env` local utilise 5433 / 6380.
- macOS : `export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"` si credential helper introuvable.

## Choix déjà actés
Voir `docs/DECISIONS.md` (ADR-001 à ADR-008).
