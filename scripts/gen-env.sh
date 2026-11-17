#!/usr/bin/env bash
# Creates .env from .env.example, replacing every "change-me" with a random value.
# Never overwrites an existing .env.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  echo "ℹ️  .env existe déjà : rien à faire (supprime-le pour le régénérer)."
  exit 0
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

while IFS= read -r line || [[ -n "$line" ]]; do
  if [[ "$line" =~ ^([A-Z0-9_]+)=change-me$ ]]; then
    # 24 random alphanumeric chars: safe in URLs, JSON and shell.
    # (finite input: no SIGPIPE under pipefail)
    value="$(openssl rand -base64 48 | LC_ALL=C tr -dc 'A-Za-z0-9' | cut -c1-24)"
    printf '%s=%s\n' "${BASH_REMATCH[1]}" "$value" >>"$tmp"
  else
    printf '%s\n' "$line" >>"$tmp"
  fi
done <.env.example

mv "$tmp" .env
chmod 600 .env
trap - EXIT
echo "✅ .env généré avec des secrets aléatoires (chmod 600)."
echo "   Mots de passe des comptes de test : grep KC_USER_ .env"
