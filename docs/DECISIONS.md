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

- **Statut** : accepté pour Compose (phase 1, vérifié) ; volet Kubernetes en phase 6
- **Contexte** : le navigateur et les conteneurs ne voient pas Keycloak à la même adresse (`localhost:8080` contre `keycloak:8080` ; `auth.localhost` pointe vers 127.0.0.1 dans un pod). L'issuer des JWT doit pourtant être unique.
- **Décision** : en Compose, `KC_HOSTNAME` fixe l'issuer public, et les services valident cet issuer tout en récupérant les clés JWKS par l'URL interne. Sur Kind, une règle de réécriture CoreDNS envoie `auth.localhost` vers le service Traefik, et la CA locale est montée dans les pods.
- **Conséquences** : la configuration des services sépare `issuer-uri` et `jwk-set-uri`.

## ADR-006 — Création des topics Kafka par un conteneur `kafka-init`

- **Statut** : accepté (phase 1)
- **Contexte** : l'auto-création des topics est désactivée, pour maîtriser partitions et réplication. Les topics doivent exister avant que les services démarrent. Or `docker compose up --wait` échoue si un conteneur s'arrête, même avec le code 0.
- **Décision** : un conteneur `kafka-init` (même image que Kafka) crée les topics de façon idempotente (`--if-not-exists`), écrit un fichier marqueur puis reste en veille. Son healthcheck vérifie ce marqueur.
- **Conséquences** : les services pourront déclarer `depends_on: kafka-init: service_healthy`. Le coût est négligeable (environ 2 Mo de RAM). Sur Kubernetes, ce rôle reviendra aux ressources `KafkaTopic` de Strimzi.

## ADR-007 — Client `dev-cli` (password grant), local uniquement

- **Statut** : accepté (phase 1)
- **Contexte** : il faut obtenir un JWT en ligne de commande pour tester les API (phases 2 et 3) avant que le frontend existe.
- **Décision** : un client public `dev-cli`, limité au *Direct Access Grant*, dans le realm local. Le client `frontend`, lui, utilise exclusivement Authorization Code avec PKCE (S256).
- **Conséquences** : le password grant est déconseillé (OAuth 2.1). Ce client sera supprimé du realm déployé sur Kubernetes.

## ADR-008 — Ports liés à 127.0.0.1 et configurables

- **Statut** : accepté (phase 1)
- **Contexte** : les ports d'infrastructure (5432, 6379…) peuvent déjà être pris sur un poste, et Kafbat UI n'a pas d'authentification.
- **Décision** : tous les ports publiés sont liés à `127.0.0.1`. Les ports côté hôte sont surchargeables dans `.env` (`*_HOST_PORT`). Les conteneurs communiquent par le réseau dédié `pme-net`.
- **Conséquences** : rien n'est exposé sur le réseau local. Un conflit de port se règle sans toucher au code.

## ADR-009 — Publication de `product-viewed` asynchrone, au plus une fois côté HTTP

- **Statut** : accepté (phase 2)
- **Contexte** : la consultation d'une fiche produit ne doit jamais ralentir ni échouer à cause de Kafka.
- **Décision** : l'événement est envoyé par une méthode `@Async`, sur des threads virtuels. Le producteur est idempotent (`acks=all`, `enable.idempotence=true`), le temps d'attente borné (`max.block.ms=10 s`) et les métadonnées préchargées au démarrage. Un échec incrémente `product_events_publish_failures_total` et est journalisé, sans donnée personnelle.
- **Conséquences** : la page reste disponible si Kafka est en panne. En contrepartie, un événement peut être perdu, ce qui est acceptable pour des recommandations. Le motif *transactional outbox* est la cible si l'on a besoin de garanties plus fortes (commandes, paiements).

## ADR-010 — Identifiants produits lisibles (slugs)

- **Statut** : accepté (phase 2)
- **Contexte** : les identifiants apparaissent dans les URL (`/produit/[id]`), les événements Kafka, les profils Valkey et les démos.
- **Décision** : des slugs (`fig-orc-evil-ed`) validés par `^[a-z0-9][a-z0-9-]{0,63}$`, côté API comme en base (contrainte CHECK).
- **Conséquences** : URL et événements restent lisibles pendant la soutenance, et la validation stricte bloque les entrées malveillantes. Il faudra gérer l'unicité des slugs lors de futures créations de produits (back-office, hors périmètre).

## ADR-011 — Journalisation structurée et corrélation

- **Statut** : accepté (phase 2)
- **Contexte** : il faut suivre une requête du frontend jusqu'au consommateur Kafka dans Loki (phase 8).
- **Décision** : logs JSON au format ECS (`logging.structured.format.console=ecs`). L'en-tête `X-Correlation-Id` est validé (sinon régénéré, contre l'injection de logs), placé dans le MDC, renvoyé dans la réponse et copié dans les headers Kafka (`correlation_id`). Le log par défaut de Spring Kafka, qui contient la charge utile complète, est désactivé.
- **Conséquences** : une seule requête Loki suffit pour suivre un parcours. Aucun identifiant utilisateur n'apparaît dans les logs applicatifs.
