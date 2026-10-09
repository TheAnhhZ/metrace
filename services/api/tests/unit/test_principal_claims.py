# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
from app.core.principal import parse_organization_claim, principal_from_claims


def test_organization_claim_object_keyed_by_alias():
    claim = {"truong-a": {"id": "8c1d"}, "nha-may-x": {"id": "77aa"}}
    assert parse_organization_claim(claim) == {"truong-a", "nha-may-x"}


def test_organization_claim_list_of_aliases():
    assert parse_organization_claim(["truong-a"]) == {"truong-a"}


def test_organization_claim_missing_or_garbage_is_empty():
    assert parse_organization_claim(None) == frozenset()
    assert parse_organization_claim("truong-a") == frozenset()
    assert parse_organization_claim([1, None]) == frozenset()


def test_principal_from_keycloak_claims():
    principal = principal_from_claims(
        {
            "sub": "u-1",
            "preferred_username": "truong-a",
            "azp": "metrace-web",
            "realm_access": {"roles": ["customer_staff", "default-roles-metrace"]},
            "organization": {"truong-a": {"id": "8c1d"}},
        }
    )
    assert principal.username == "truong-a"
    assert principal.org_aliases == {"truong-a"}
    assert "customer_staff" in principal.roles
    assert principal.is_internal is False
    assert principal.client_id == "metrace-web"


def test_internal_role_marks_principal_internal():
    principal = principal_from_claims({"sub": "u-2", "realm_access": {"roles": ["chef"]}})
    assert principal.is_internal is True
    assert principal.username == "u-2"
    assert principal.org_aliases == frozenset()
