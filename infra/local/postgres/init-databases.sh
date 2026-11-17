#!/usr/bin/env bash
# Creates one database + one owner role per application.
# Executed once by the official postgres image (docker-entrypoint-initdb.d)
# when the data volume is empty. Credentials come from the environment (.env).
set -euo pipefail

create_db() {
  local db="$1" user="$2" password="$3"
  echo "Creating role '${user}' and database '${db}'"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
    --set=db="$db" --set=user="$user" --set=password="$password" <<-'EOSQL'
	CREATE ROLE :"user" WITH LOGIN PASSWORD :'password';
	CREATE DATABASE :"db" OWNER :"user";
	REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
EOSQL
}

create_db "$CATALOG_DB_NAME" "$CATALOG_DB_USER" "$CATALOG_DB_PASSWORD"
create_db "$KEYCLOAK_DB_NAME" "$KEYCLOAK_DB_USER" "$KEYCLOAK_DB_PASSWORD"
