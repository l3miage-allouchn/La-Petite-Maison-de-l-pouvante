# La Petite Maison de l'Épouvante — developer entry points
# Run `make help` to list targets.
SHELL := /bin/bash
.DEFAULT_GOAL := help

MODE ?= compose

define todo
	@echo "⏳ '$@' : à venir en $(1)."
endef

.PHONY: help bootstrap infra dev dev-down dev-reset test \
        cluster platform secrets up down demo-broker

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

bootstrap: ## Prépare le poste : .env + hooks pre-commit
	@test -f .env || { cp .env.example .env && echo "✅ .env créé depuis .env.example — remplace les valeurs change-me"; }
	pre-commit install

# ---------- Partie A : Docker Compose ----------
infra: ## Démarre l'infrastructure seule (Postgres, Kafka, Valkey, Keycloak, UI Kafka)
	$(call todo,phase 1)

dev: ## Démarre toute l'application (infra + 3 services)
	$(call todo,phase 1)

dev-down: ## Arrête la stack Compose
	$(call todo,phase 1)

dev-reset: ## Arrête la stack Compose et supprime les volumes
	$(call todo,phase 1)

test: ## Lance les tests de tous les services
	$(call todo,phases 2 à 4)

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
