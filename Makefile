# La Petite Maison de l'Épouvante — developer entry points
# Run `make help` to list targets.
SHELL := /bin/bash
.DEFAULT_GOAL := help

MODE ?= compose
# Java 25 LTS (Homebrew's default openjdk may be newer and non-LTS)
# (`java_home -v 25` silently returns a newer JDK when 25 is not registered, so check the brew path first.)
BREW_JDK25  := /opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home
JAVA25_HOME ?= $(if $(wildcard $(BREW_JDK25)),$(BREW_JDK25),$(JAVA_HOME))
COMPOSE       := docker compose --env-file .env
COMPOSE_INFRA := $(COMPOSE) -f docker-compose.infra.yml
COMPOSE_ALL   := $(COMPOSE) -f docker-compose.yml

define todo
	@echo "⏳ '$@' : à venir en $(1)."
endef

.PHONY: help env bootstrap check-env infra infra-down status logs kafka-demo-event test-catalog test-reco reco-offline reco-replay dev dev-down dev-reset test \
        cluster platform secrets up down demo-broker

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

env: ## Génère .env avec des secrets aléatoires (ne l'écrase jamais)
	@./scripts/gen-env.sh

bootstrap: env ## Prépare le poste : .env + hooks pre-commit
	pre-commit install

check-env:
	@test -f .env || { echo "❌ .env manquant : lance 'make env'"; exit 1; }

# ---------- Partie A : Docker Compose ----------
infra: check-env ## Démarre l'infrastructure seule (Postgres, Kafka, Valkey, Keycloak, UI Kafka)
	$(COMPOSE_INFRA) up -d --wait
	@$(MAKE) --no-print-directory status

infra-down: ## Arrête l'infrastructure seule
	$(COMPOSE_INFRA) down

dev: check-env ## Démarre toute l'application (infra + 3 services)
	$(COMPOSE_ALL) up -d --build --wait
	@$(MAKE) --no-print-directory status

dev-down: ## Arrête la stack Compose
	$(COMPOSE_ALL) down

dev-reset: ## Arrête la stack Compose et supprime les volumes (données perdues)
	$(COMPOSE_ALL) down -v --remove-orphans

status: ## État des conteneurs
	@$(COMPOSE_ALL) ps --format 'table {{.Service}}\t{{.Status}}\t{{.Ports}}'

logs: ## Suit les logs (S=service pour filtrer)
	$(COMPOSE_ALL) logs -f $(S)

kafka-demo-event: ## Publie un événement product-viewed de test dans Kafka
	@./infra/local/kafka/produce-demo-event.sh

test: test-catalog test-reco ## Lance les tests de tous les services

test-catalog: ## catalog-service : tests unitaires + intégration (Testcontainers) + couverture
	cd services/catalog-service && JAVA_HOME=$(JAVA25_HOME) ./mvnw -B verify

test-reco: ## reco-service : ruff + mypy + pytest (unitaires + Testcontainers) + couverture
	cd services/reco-service && uv run ruff check . && uv run ruff format --check . && uv run mypy \
		&& uv run pytest --cov --cov-report=term --cov-report=xml

reco-offline: ## Modèle de reco hors-ligne sur les événements de démo (ARGS="--evaluate")
	cd services/reco-service && uv run python -m app.model.offline $(ARGS)

reco-replay: check-env ## Rejoue tout l'historique Kafka pour reconstruire les profils de reco
	@./scripts/reco-replay.sh

# ---------- Partie B : Kubernetes ----------
cluster: ## Crée le cluster Kind
	$(call todo,phase 6)

platform: ## Installe ArgoCD et l'app racine (GitOps)
	$(call todo,phase 6)

secrets: ## Crée/met à jour les Secrets Kubernetes depuis .env
	$(call todo,phase 6)

up: ## cluster + platform + secrets
	$(call todo,phase 6)

down: ## Supprime le cluster Kind
	$(call todo,phase 6)

# ---------- Démos ----------
demo-broker: ## Benchmark Kafka vs RabbitMQ (MODE=compose|k8s)
	$(call todo,phase 9)
