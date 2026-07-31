"""
Router tests for GET/POST/PATCH/DELETE /v1/configs/{namespace}
and GET /v1/scopes.

Focuses on:
- scope_identifiers Option-B parsing (?scope_identifiers=key:value)
- multi-scope merging
- 422 on malformed scope_identifiers
- 404 for missing namespace
"""

from ficus.services.utils import DEFAULT_MODE


BASE = "/v1/configs"


# ---------------------------------------------------------------------------
# GET /v1/scopes
# ---------------------------------------------------------------------------

def test_get_scopes_returns_set(client):
    response = client.get("/v1/scopes")
    assert response.status_code == 200
    scopes = response.json()
    assert "hostname" in scopes
    assert "subject_id" in scopes


# ---------------------------------------------------------------------------
# GET /{namespace}  →  merged ConfigDataResponse
# ---------------------------------------------------------------------------

def test_get_config_default_scope_returns_merged_data(client):
    response = client.get(f"{BASE}/software_a")
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Successfully retrieved configuration"
    assert "default-default-value" in body["config"]["data"]


def test_get_config_with_single_scope_identifier(client):
    response = client.get(
        f"{BASE}/software_a",
        params={"scope_identifiers": "hostname:w11dt000001"},
    )
    assert response.status_code == 200
    data = response.json()["config"]["data"]
    assert "default-default-value" in data
    assert "computer-default-value" in data


def test_get_config_with_multiple_scope_identifiers(client):
    response = client.get(
        f"{BASE}/software_a",
        params=[
            ("scope_identifiers", "hostname:w11dt000001"),
            ("scope_identifiers", "subject_id:614173"),
        ],
    )
    assert response.status_code == 200
    data = response.json()["config"]["data"]
    assert "default-default-value" in data
    assert "computer-default-value" in data
    assert "subject-default-value" in data


def test_get_config_not_found_returns_404(client):
    response = client.get(f"{BASE}/nonexistent_namespace")
    assert response.status_code == 404


def test_get_all_modes(client):
    response = client.get(
        f"{BASE}/software_a/modes",
        params={
            "lowest_scope_only": False,
            "scope_identifiers": "hostname:w10dtburno"},
    )
    assert response.json() == ['config', DEFAULT_MODE]


# ---------------------------------------------------------------------------
# scope_identifiers format validation (Option B)
# ---------------------------------------------------------------------------

def test_get_config_bad_scope_identifier_missing_colon_returns_422(client):
    response = client.get(
        f"{BASE}/software_a",
        params={"scope_identifiers": "badformat"},
    )
    assert response.status_code == 422
    assert "key:value" in response.json()["detail"]


def test_get_config_scope_identifier_with_colon_in_value(client):
    """Values containing ':' should be preserved (split on first colon only)."""
    # A scope identifier like "env:us:east" should parse key="env", value="us:east".
    # The namespace won't exist so we expect 404, not 422.
    response = client.get(
        f"{BASE}/software_a",
        params={"scope_identifiers": "hostname:us:east"},
    )
    # Parsing succeeds (no 422); the namespace/scope lookup may 404 but format is valid
    assert response.status_code != 422


# ---------------------------------------------------------------------------
# POST /{namespace}
# ---------------------------------------------------------------------------

def test_post_config_creates_file(client):
    response = client.post(
        f"{BASE}/new_app",
        json={"setting": "value"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully saved configuration file"


def test_post_config_with_scope_identifier(client):
    # Use a namespace that doesn't exist yet so the override stack is empty
    # and save_config creates a fresh file — isolating the routing/parsing logic.
    response = client.post(
        f"{BASE}/new_scoped_app",
        params={"scope_identifiers": "hostname:w11dt000001"},
        json={"new-setting": "value"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# PATCH /{namespace}
# ---------------------------------------------------------------------------

def test_patch_config_updates_file(client):
    # append_new_fields_to_last_scope=True required because "new-key" does not
    # exist in any level of the current override stack.
    response = client.patch(
        f"{BASE}/software_a",
        params={"append_new_fields_to_last_scope": "true"},
        json={"new-key": "patched"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully updated configuration file"


# ---------------------------------------------------------------------------
# DELETE /{namespace}
# ---------------------------------------------------------------------------

def test_delete_config(client):
    response = client.delete(f"{BASE}/software_a")
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully deleted configuration file"
