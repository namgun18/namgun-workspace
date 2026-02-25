#!/bin/bash
set -e

# Gitea DB 생성 (DB_USER가 누구든 동작)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE gitea OWNER "$POSTGRES_USER";
EOSQL
