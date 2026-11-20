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

## ADR-012 — Modèle de recommandation isolé derrière une interface et un registre

- **Statut** : accepté (phase 3)
- **Contexte** : la data scientist doit pouvoir remplacer l'algorithme sans toucher au consommateur, à l'API ni à la sécurité.
- **Décision** : une interface abstraite `Recommender` (`update`, `recommend`, `similar`), un registre choisi par la variable `RECO_MODEL`, et un `FeatureStore` en deux implémentations (Valkey et mémoire). Un bac à sable hors-ligne (`app/model/offline.py`) mesure HitRate@k et MRR@k sur un jeu d'événements de démo.
- **Conséquences** : le modèle s'expérimente sans Docker, et changer de modèle revient à changer une variable d'environnement. Le modèle de base (co-occurrence et affinité, pondérées par la récence) sert de référence chiffrée : HitRate@4 = 0,50.

## ADR-013 — Synchronisation périodique du catalogue dans reco-service

- **Statut** : accepté (phase 3)
- **Contexte** : à partir des seuls événements, un produit jamais consulté ne peut jamais être recommandé (démarrage à froid côté produit).
- **Décision** : reco-service importe le catalogue (`GET /api/catalog/products`, paginé) au démarrage puis toutes les 10 minutes. Chaque produit est enregistré avec une popularité de 0. Un échec n'empêche ni le démarrage ni le service.
- **Conséquences** : tous les produits peuvent être recommandés via l'affinité de catégorie ou d'univers. Cela crée une dépendance réseau faible reco → catalogue, à autoriser explicitement dans les NetworkPolicy (phase 7).

## ADR-014 — Sémantique de consommation : au moins une fois, DLQ, dédoublonnage

- **Statut** : accepté (phase 3)
- **Contexte** : il ne faut ni perdre d'événements ni bloquer le flux sur un message corrompu.
- **Décision** : commit manuel des offsets après traitement. Un message invalide (JSON ou schéma) part dans `catalog.product-viewed.dlq` avec ses en-têtes d'origine, plus `dlq_reason` et `dlq_source`. Une erreur transitoire (Valkey indisponible) déclenche des nouvelles tentatives avec backoff, sans commit. Le dédoublonnage par `event_id` (TTL 24 h) n'est marqué qu'une fois le traitement réussi.
- **Conséquences** : pas de perte en cas de panne de Valkey, puisque le lag Kafka absorbe le retard (alerte prévue en phase 8). Un rejeu complet reste possible (`make reco-replay`) grâce à la rétention Kafka. C'est l'un des arguments de la comparaison Kafka/RabbitMQ (phase 9).

## ADR-015 — Frontend : jetons côté serveur uniquement (Auth.js v5)

- **Statut** : accepté (phase 4)
- **Contexte** : un jeton d'accès exposé au JavaScript du navigateur peut être volé par une faille XSS.
- **Décision** : Next.js rend les pages côté serveur et appelle lui-même catalog-service et reco-service. Auth.js v5 (`next-auth@5.0.0-beta.32`, seule version compatible Next 16 ; la v4 n'est plus maintenue) conserve les jetons dans un cookie de session chiffré, HttpOnly. La session exposée au client ne contient que le `sub`. Le rafraîchissement du jeton est fait côté serveur.
- **Conséquences** : aucun jeton dans le navigateur, aucun CORS à ouvrir sur les API. Dépendance à une version bêta, épinglée exactement et suivie par Dependabot.

## ADR-016 — Endpoints Keycloak explicites (pas de découverte OIDC)

- **Statut** : accepté (phase 4)
- **Contexte** : sous Compose, le navigateur joint Keycloak via `localhost:8080` tandis que le conteneur frontend le joint via `keycloak:8080` (voir ADR-005). La découverte OIDC renverrait des URL inaccessibles pour l'un ou l'autre.
- **Décision** : l'URL d'autorisation utilise l'issuer public ; les URL de jeton, userinfo et de rafraîchissement utilisent l'issuer interne. L'issuer attendu dans les jetons reste l'URL publique.
- **Conséquences** : fonctionne sans bricolage DNS sous Compose. En Kubernetes (phase 7), les deux variables pointeront vers `https://auth.localhost` (ou le service interne pour le backchannel).

## ADR-017 — CSP stricte avec nonce, styles en `unsafe-inline`

- **Statut** : accepté (phase 4)
- **Contexte** : la CSP est la principale défense contre le XSS ; Next.js injecte des scripts inline.
- **Décision** : nonce aléatoire par requête (généré dans `proxy.ts`) pour `script-src` avec `strict-dynamic` ; `form-action` limité à `'self'` et à l'origine Keycloak (les navigateurs appliquent `form-action` aux redirections du formulaire de connexion) ; `frame-ancestors 'none'`. `style-src` garde `'unsafe-inline'` (styles injectés par Next/next-font), risque faible sans exécution de script.
- **Conséquences** : pages rendues dynamiquement (pas de cache statique), acceptable pour la démo. Le scan ZAP (phase 5) vérifiera les en-têtes.

## ADR-018 — Tests de bout en bout sur la stack réelle, un seul worker

- **Statut** : accepté (phase 4)
- **Contexte** : le parcours démontré traverse Keycloak, le catalogue, Kafka et la reco ; des tests avec mocks ne le prouveraient pas.
- **Décision** : Playwright cible la stack Compose lancée (`make test-e2e`) ; le mot de passe de l'utilisateur de test vient de `.env`. Les tests tournent sur un seul worker : une seule stack partagée sur un poste de 16 Go, et Keycloak en mode dev compile son thème à la première connexion. axe-core sert d'indicateur RGAA automatisé (WCAG 2.1 A/AA).
- **Conséquences** : environ 25 s pour 12 tests, déterministes. En CI (phase 5), la même suite tournera contre la stack démarrée dans le runner.
