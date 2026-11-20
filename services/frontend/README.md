# frontend

Vitrine Next.js de La Petite Maison de l'Épouvante (phase 4). Vue d'ensemble, pages et choix de sécurité :
voir la section « Frontend » du [README principal](../../README.md) et les ADR-015 à ADR-018.

## Développement local

```bash
make infra                      # depuis la racine : Postgres, Kafka, Valkey, Keycloak
# + catalog-service et reco-service (make dev lance tout, frontend compris)
cp ../../.env .env.local        # puis ne garder que les variables utiles (fichier ignoré par Git)
npm ci
npm run dev                     # http://localhost:3000
```

Variables attendues (voir `docker-compose.yml`) : `AUTH_SECRET`, `AUTH_URL`, `AUTH_KEYCLOAK_ID`,
`AUTH_KEYCLOAK_SECRET`, `KEYCLOAK_ISSUER`, `KEYCLOAK_INTERNAL_ISSUER`, `CATALOG_API_URL`, `RECO_API_URL`.

## Tests

```bash
npm run lint && npm run typecheck && npm test   # = make test-frontend
npx playwright install chromium                 # une seule fois
make test-e2e                                   # depuis la racine, stack lancée
```

## Structure

- `src/app/` : pages (App Router), actions serveur de connexion/déconnexion, route `/api/health`.
- `src/lib/` : client API serveur, configuration, session/jetons, en-têtes de sécurité.
- `src/proxy.ts` : nonce CSP, identifiant de session anonyme, identifiant de corrélation.
- `e2e/` : Playwright (parcours visiteur, parcours connecté, audit axe).
