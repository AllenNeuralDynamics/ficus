"""
Router tests for GET/POST/PATCH/DELETE /v1/leaves/{namespace}[/raw].

These tests focus on routing behaviour, response shapes, and HTTP status codes.
Service-layer logic is covered by tests/unit/services/test_leaf_crud.py.
"""
import pytest


BASE = "/v1/leaves"


# ---------------------------------------------------------------------------
# GET /{namespace}  →  parsed dict
# ---------------------------------------------------------------------------

def test_get_leaf_data_returns_parsed_dict(client):
    response = client.get(f"{BASE}/software_a")
    assert response.status_code == 200
    data = response.json()
    assert "default-default-value" in data


def test_get_leaf_data_with_scope(client):
    response = client.get(
        f"{BASE}/software_a",
        params={"scope": "hostname", "scope_identifier": "w11dt000001"},
    )
    assert response.status_code == 200
    assert "computer-default-value" in response.json()

def test_get_leaf_data_with_mode(client):
    response = client.get(
        f"{BASE}/software_a",
        params={"mode": "config"},
    )
    assert response.status_code == 200
    expected = {
                        "name": "config",
                        "scope": "default",
                        "default-layer-value": "beep beep"
                    }
    assert response.json() == expected


def test_get_leaf_data_not_found_returns_404(client):
    response = client.get(f"{BASE}/nonexistent_namespace")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# scope / scope_identifier pair validation
# ---------------------------------------------------------------------------

def test_get_leaf_scope_without_identifier_returns_422(client):
    response = client.get(f"{BASE}/software_a", params={"scope": "hostname"})
    assert response.status_code == 422
    assert "scope_identifier" in response.json()["detail"]


def test_get_leaf_identifier_without_scope_returns_422(client):
    response = client.get(f"{BASE}/software_a", params={"scope_identifier": "w11dt000001"})
    assert response.status_code == 422
    assert "scope" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /{namespace}/raw  →  {"content": str, "suffix": str}
# ---------------------------------------------------------------------------

def test_get_leaf_raw_returns_content_and_suffix(client):
    response = client.get(f"{BASE}/software_a/raw")
    assert response.status_code == 200
    body = response.json()
    assert "content" in body
    assert "suffix" in body
    assert body["suffix"] == ".yml"


def test_get_leaf_raw_with_json_scope_returns_json_suffix(client):
    response = client.get(
        f"{BASE}/software_a/raw",
        params={"scope": "hostname", "scope_identifier": "w11dt000001"},
    )
    assert response.status_code == 200
    assert response.json()["suffix"] == ".json"


def test_get_leaf_raw_not_found_returns_404(client):
    response = client.get(f"{BASE}/nonexistent_namespace/raw")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /{namespace}  →  create from dict body
# ---------------------------------------------------------------------------

def test_post_leaf_data_creates_leaf(client):
    response = client.post(
        f"{BASE}/new_app",
        params={"suffix": ".yml"},
        json={"key": "value"},
    )
    assert response.status_code == 200
    assert response.json() == {"key": "value"}


def test_post_leaf_data_conflict_returns_409(client):
    # software_a/default.yml already exists in the fixture store
    response = client.post(
        f"{BASE}/software_a",
        params={"suffix": ".yml"},
        json={"key": "value"},
    )
    assert response.status_code == 409


def test_post_leaf_data_overwrite_succeeds(client):
    response = client.post(
        f"{BASE}/software_a",
        params={"suffix": ".yml", "overwrite": "true"},
        json={"overwritten": True},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /{namespace}/raw  →  create from raw string
# ---------------------------------------------------------------------------

def test_post_leaf_raw_creates_leaf(client):
    response = client.post(
        f"{BASE}/new_raw_app/raw",
        params={"suffix": ".yml", "content": "key: value\n"},
    )
    assert response.status_code == 200
    assert response.json() == {"content": "key: value\n"}


def test_post_leaf_raw_conflict_returns_409(client):
    response = client.post(
        f"{BASE}/software_a/raw",
        params={"suffix": ".yml", "content": "key: value\n"},
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# PATCH /{namespace}  →  deep-merge dict into existing leaf
# ---------------------------------------------------------------------------

def test_patch_leaf_data_merges_keys(client):
    response = client.patch(
        f"{BASE}/software_a",
        json={"new-key": "new-value"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["new-key"] == "new-value"
    assert data["default-default-value"] == "the one ring"


def test_patch_leaf_data_not_found_returns_404(client):
    response = client.patch(f"{BASE}/nonexistent_namespace", json={"k": "v"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /{namespace}
# ---------------------------------------------------------------------------

def test_delete_leaf_returns_leaf_path(client):
    response = client.delete(f"{BASE}/software_a")
    assert response.status_code == 200
    assert "leaf_path" in response.json()


def test_delete_leaf_then_get_returns_404(client):
    client.delete(f"{BASE}/software_a")
    assert client.get(f"{BASE}/software_a").status_code == 404


def test_delete_leaf_not_found_returns_404(client):
    response = client.delete(f"{BASE}/nonexistent_namespace")
    assert response.status_code == 404
