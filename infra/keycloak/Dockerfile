# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# Keycloak built from the Apache-2.0 distribution on an OSI base image.
# The official image uses Red Hat UBI (non-OSI EULA), so we build our own.
FROM eclipse-temurin:21-jre AS build
ARG KC_VERSION=26.8.0
ARG KC_SHA1=0733c575b7e162a0cf3ff7e658702ac4775b3f6c
ADD https://github.com/keycloak/keycloak/releases/download/${KC_VERSION}/keycloak-${KC_VERSION}.tar.gz /tmp/kc.tgz
RUN echo "${KC_SHA1}  /tmp/kc.tgz" | sha1sum -c - \
 && tar -xzf /tmp/kc.tgz -C /opt \
 && mv /opt/keycloak-${KC_VERSION} /opt/keycloak \
 && rm /tmp/kc.tgz
# Build-time options are baked in so the runtime can use `start --optimized`.
# Admin console (`admin`) and account console (`account`) are disabled;
# the admin REST API (`admin-api`) stays on for the one-shot kc-bootstrap.
RUN /opt/keycloak/bin/kc.sh build \
      --db=postgres \
      --health-enabled=true \
      --http-relative-path=/auth \
      --features-disabled=admin,account

FROM eclipse-temurin:21-jre
COPY --from=build --chown=1000:1000 /opt/keycloak /opt/keycloak
COPY --chown=1000:1000 realm-metrace.json /opt/keycloak/data/import/realm-metrace.json
COPY --chown=1000:1000 healthcheck.sh /opt/keycloak/healthcheck.sh
USER 1000
EXPOSE 8080 9000
ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
CMD ["start", "--optimized", "--import-realm"]
