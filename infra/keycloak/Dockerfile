# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
#
# Official Keycloak image from the publisher (quay.io/keycloak).
# OLP organisers (09/10/2026): standalone software used as a service does not
# count toward the project's source licence, so the UBI base layer is fine.
FROM quay.io/keycloak/keycloak:26.8.0 AS build
# Build-time options are baked in so the runtime can use `start --optimized`.
# Admin console (`admin`) and account console (`account`) are disabled;
# the admin REST API (`admin-api`) stays on for the one-shot kc-bootstrap.
RUN /opt/keycloak/bin/kc.sh build \
      --db=postgres \
      --health-enabled=true \
      --http-relative-path=/auth \
      --features-disabled=admin,account

FROM quay.io/keycloak/keycloak:26.8.0
COPY --from=build /opt/keycloak/ /opt/keycloak/
COPY --chown=1000:0 realm-metrace.json /opt/keycloak/data/import/realm-metrace.json
COPY --chown=1000:0 healthcheck.sh /opt/keycloak/healthcheck.sh
EXPOSE 8080 9000
ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
CMD ["start", "--optimized", "--import-realm"]
