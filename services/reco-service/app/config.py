"""Configuration from environment variables (12-factor). No secret has a default value."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    # --- Kafka ---
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "catalog.product-viewed"
    kafka_dlq_topic: str = "catalog.product-viewed.dlq"
    kafka_group_id: str = "reco-service"
    consumer_enabled: bool = True

    # --- Valkey ---
    valkey_host: str = "localhost"
    valkey_port: int = 6379
    valkey_password: SecretStr | None = None
    valkey_key_prefix: str = "reco:"

    # --- OIDC (Keycloak) — public issuer, internal JWKS URL (ADR-005) ---
    oidc_issuer_uri: str = "http://localhost:8080/realms/petite-maison"
    oidc_jwk_set_uri: str = "http://localhost:8080/realms/petite-maison/protocol/openid-connect/certs"
    oidc_audience: str = "catalog-api"

    # --- Catalog sync (knows every product, even never viewed ones) ---
    catalog_api_url: str | None = "http://localhost:8081"
    catalog_sync_interval_seconds: int = Field(default=600, ge=30)

    # --- Model ---
    reco_model: str = "cooccurrence"

    # --- HTTP ---
    cors_allowed_origins: list[str] = ["http://localhost:3000"]
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"


@lru_cache
def get_settings() -> Settings:
    return Settings()
