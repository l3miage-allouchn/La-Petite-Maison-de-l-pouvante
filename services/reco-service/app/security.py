"""JWT validation against Keycloak (signature from JWKS, issuer, audience, expiry)."""

import logging
from dataclasses import dataclass

import anyio
import jwt
from jwt import PyJWKClient

log = logging.getLogger(__name__)


class InvalidTokenError(Exception):
    """The bearer token is missing, malformed, expired or not issued for this API."""


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    username: str | None
    roles: frozenset[str]


class JwtVerifier:
    def __init__(self, issuer: str, audience: str, jwks_url: str) -> None:
        self._issuer = issuer
        self._audience = audience
        # Keys are cached and refreshed on unknown "kid" (key rotation).
        self._jwks = PyJWKClient(jwks_url, cache_keys=True, lifespan=300, timeout=5)

    async def verify(self, token: str) -> Principal:
        try:
            # PyJWKClient does blocking HTTP: keep it off the event loop.
            signing_key = await anyio.to_thread.run_sync(self._jwks.get_signing_key_from_jwt, token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
                leeway=10,
            )
        except jwt.PyJWTError as exc:
            log.info("JWT rejected: %s", type(exc).__name__)
            raise InvalidTokenError(str(exc)) from exc
        realm_access = claims.get("realm_access") or {}
        roles = realm_access.get("roles", []) if isinstance(realm_access, dict) else []
        return Principal(
            subject=str(claims["sub"]),
            username=claims.get("preferred_username"),
            roles=frozenset(str(r) for r in roles),
        )
