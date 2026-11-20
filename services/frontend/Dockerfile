# syntax=docker/dockerfile:1
# Next.js standalone output: only the server bundle and its traced dependencies, non-root user.

# ---------- dependencies ----------
FROM node:26.13.1-alpine3.24 AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

# ---------- build ----------
FROM deps AS build
ENV NEXT_TELEMETRY_DISABLED=1
COPY . .
# next/font downloads the fonts here (build time), so visitors never call Google.
RUN npm run build

# ---------- runtime ----------
FROM node:26.13.1-alpine3.24

LABEL org.opencontainers.image.title="frontend" \
      org.opencontainers.image.description="La Petite Maison de l'Épouvante - storefront" \
      org.opencontainers.image.source="https://github.com/l3miage-allouchn/La-Petite-Maison-de-l-pouvante" \
      org.opencontainers.image.licenses="MIT"

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup -S -g 10001 app && adduser -S -D -H -u 10001 -G app -s /sbin/nologin app
WORKDIR /app

# Owned by root (read-only for the app user). Runtime cache: /app/.next/cache (tmpfs / emptyDir).
COPY --from=build /app/public ./public
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static

USER 10001:10001
EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=5 \
  CMD wget -qO- http://127.0.0.1:3000/api/health | grep -q '"UP"' || exit 1

CMD ["node", "server.js"]
