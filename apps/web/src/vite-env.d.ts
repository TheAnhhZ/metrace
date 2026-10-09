// SPDX-FileCopyrightText: The metrace Authors
// SPDX-License-Identifier: Apache-2.0
/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Keycloak base URL incl. /auth. Default: http://localhost:9080/auth */
  readonly VITE_KEYCLOAK_URL?: string;
  /** Default: metrace */
  readonly VITE_KEYCLOAK_REALM?: string;
  /** Default: metrace-web */
  readonly VITE_KEYCLOAK_CLIENT_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
