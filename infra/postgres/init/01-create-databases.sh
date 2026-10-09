#!/usr/bin/env bash
# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# Runs once on an empty data volume. Creates one database per core service.
# metrace uses two roles: metrace_migrator (schema owner, runs alembic) and
# metrace_app (runtime; cannot UPDATE/DELETE audit_event, see migrations).
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-SQL
  CREATE ROLE keycloak LOGIN PASSWORD '${KC_DB_PASSWORD}';
  CREATE DATABASE keycloak OWNER keycloak;

  CREATE ROLE flowable LOGIN PASSWORD '${FLOWABLE_DB_PASSWORD}';
  CREATE DATABASE flowable OWNER flowable;

  CREATE ROLE metrace_migrator LOGIN PASSWORD '${METRACE_MIGRATOR_PASSWORD}';
  CREATE ROLE metrace_app LOGIN PASSWORD '${METRACE_APP_PASSWORD}';
  CREATE DATABASE metrace OWNER metrace_migrator;
SQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname metrace <<-SQL
  REVOKE ALL ON SCHEMA public FROM PUBLIC;
  GRANT USAGE ON SCHEMA public TO metrace_app;
  ALTER SCHEMA public OWNER TO metrace_migrator;
SQL
