# Journal des décisions d'architecture (ADR)

Format court : contexte → décision → conséquences. Statuts : *proposé*, *accepté*, *remplacé*.

---

## ADR-001 — Monorepo

- **Statut** : accepté (phase 0)
- **Contexte** : 3 services, l'infrastructure et le GitOps sont développés par une équipe de deux.
- **Décision** : un seul dépôt (`services/`, `infra/`, `gitops/`, `demos/`, `docs/`). Les workflows CI sont filtrés par chemin.
- **Conséquences** : une seule source de vérité et des changements transverses atomiques. ArgoCD lit le même dépôt, et la CI commitera les tags d'image dans `gitops/`.

## ADR-002 — Secrets : `.env` local et Secrets Kubernetes natifs

- **Statut** : accepté (phase 0)
- **Contexte** : aucun secret ne doit entrer dans Git, et l'outillage doit rester simple pour une démo locale.
- **Décision** : un `.env` ignoré par Git (modèle `.env.example` commité). En CI, des secrets GitHub. Dans le cluster, `make secrets` crée des Secrets Kubernetes à partir du `.env`. Gitleaks tourne en pre-commit et en CI, avec la push protection de GitHub.
- **Conséquences** : pas de rotation automatique ni de chiffrement au repos des Secrets (etcd Kind). La cible de production (External Secrets avec OpenBao) sera décrite dans `docs/SECURITY.md`.

## ADR-003 — Images multi-architecture (amd64 + arm64)

- **Statut** : accepté (phase 0)
- **Contexte** : le poste de développement est un Mac Apple Silicon (arm64), alors que les runners GitHub sont en amd64.
- **Décision** : Buildx publie des images multi-arch (`linux/amd64,linux/arm64`). Cosign signe l'index.
- **Conséquences** : le build CI est plus long (QEMU), mais les images tournent nativement dans Kind sur le Mac.

## ADR-004 — Interface Kafka : Kafbat UI

- **Statut** : accepté (phase 0)
- **Contexte** : il faut visualiser les messages pendant les démos.
- **Décision** : Kafbat UI (licence Apache 2.0, image officielle `ghcr.io/kafbat/kafka-ui`), plutôt que Redpanda Console (licence BSL).
- **Conséquences** : licence permissive. Outil limité au mode Compose et aux démos.

## ADR-005 — Résolution de l'issuer OIDC (Keycloak)

- **Statut** : proposé (mis en œuvre en phases 1 et 6)
- **Contexte** : le navigateur et les conteneurs ne voient pas Keycloak à la même adresse (`localhost:8080` contre `keycloak:8080` ; `auth.localhost` pointe vers 127.0.0.1 dans un pod). L'issuer des JWT doit pourtant être unique.
- **Décision** : en Compose, `KC_HOSTNAME` fixe l'issuer public, et les services valident cet issuer tout en récupérant les clés JWKS par l'URL interne. Sur Kind, une règle de réécriture CoreDNS envoie `auth.localhost` vers le service Traefik, et la CA locale est montée dans les pods.
- **Conséquences** : la configuration des services sépare `issuer-uri` et `jwk-set-uri`.
