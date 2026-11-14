from pathlib import Path

import pytest

from ficus.database.filesys import FileSysStore
from ficus.services.scopes import ScopeExistsError, add_scope


def _stack(response):
    """The override stack as (scope, identifier) pairs; defaults as ("defaults", None)."""
    pairs = []
    for path in response.json()["config"]["override_stack"]:
        parts = Path(path).parts
        if "defaults" in parts:
            pairs.append(("defaults", None))
        else:
            ns_index = parts.index("software_a")
            pairs.append((parts[ns_index - 2], parts[ns_index - 1]))
    return pairs


EXPECTED = [("defaults", None), ("hostname", "w11dt000001"), ("subject_id", "614173")]


def test_scope_param_merges_in_ficus_precedence_whatever_the_order(client):
    response = client.get(
        "/v1/configs/software_a?scope=subject_id:614173&scope=hostname:w11dt000001"
    )
    assert response.status_code == 200
    assert _stack(response) == EXPECTED


def test_legacy_scope_params_follow_the_same_precedence(client):
    response = client.get("/v1/configs/software_a?subject_id=614173&hostname=w11dt000001")
    assert response.status_code == 200
    assert _stack(response) == EXPECTED


def test_both_styles_agree(client):
    new = client.get("/v1/configs/software_a?scope=hostname:w11dt000001&scope=subject_id:614173")
    old = client.get("/v1/configs/software_a?hostname=w11dt000001&subject_id=614173")
    assert new.json()["config"]["data"] == old.json()["config"]["data"]


@pytest.mark.parametrize(
    "query, detail",
    [
        ("scope=hostname:w11dt000001&subject_id=614173", "not both"),
        ("scope=room:R1", "Unknown scope"),
        ("scope=hostname:a&scope=hostname:b", "more than once"),
        ("hostname=a&hostname=b", "more than once"),
        ("scope=hostname", "<scope>:<identifier>"),
        ("scope=:x", "<scope>:<identifier>"),
        ("scope=hostname:", "<scope>:<identifier>"),
    ],
)
def test_bad_scope_queries_are_refused(client, query, detail):
    response = client.get(f"/v1/configs/software_a?{query}")
    assert response.status_code == 422
    assert detail in response.json()["detail"]


def test_saving_to_an_unknown_scope_is_refused_and_creates_nothing(client, filesys_store):
    response = client.post("/v1/configs/software_a?scope=room:R1", json={"a": 1})
    assert response.status_code == 422
    assert not filesys_store.exists(filesys_store.rootdir / "room")


def test_leaf_writes_to_an_unknown_scope_are_refused_and_create_nothing(client, filesys_store):
    response = client.post(
        "/v1/leaves/software_a?scope=typo_scope&scope_identifier=X&suffix=.json&mode=default",
        json={"b": 2},
    )
    assert response.status_code == 422
    assert "Unknown scope" in response.json()["detail"]
    assert not filesys_store.exists(filesys_store.rootdir / "typo_scope")


def test_leaf_writes_to_a_created_scope_work(client):
    client.post("/v1/scopes/room")
    response = client.post(
        "/v1/leaves/software_a?scope=room&scope_identifier=R1&suffix=.json&mode=default",
        json={"b": 2},
    )
    assert response.status_code == 200


def test_scopes_are_listed_in_precedence_order(client):
    assert client.get("/v1/scopes").json() == ["hostname", "subject_id"]


def test_a_new_scope_needs_its_own_endpoint_and_then_works_everywhere(client, filesys_store):
    created = client.post("/v1/scopes/room")
    assert created.status_code == 201
    assert created.json() == ["hostname", "subject_id", "room"]
    assert client.get("/v1/scopes").json() == ["hostname", "subject_id", "room"]
    assert filesys_store.exists(filesys_store.rootdir / "room")

    saved = client.post(
        "/v1/configs/software_a?scope=room:R1&append_new_fields_to_last_scope=true",
        json={"room-value": "lab 3"},
    )
    assert saved.status_code == 200
    merged = client.get("/v1/configs/software_a?scope=room:R1&scope=hostname:w11dt000001")
    assert merged.json()["config"]["data"]["room-value"] == "lab 3"
    assert [p for p, _ in _stack(merged)] == ["defaults", "hostname", "room"]
    assert client.get("/v1/scopes/room").json() == ["R1"]


def test_creating_a_scope_twice_conflicts(client):
    assert client.post("/v1/scopes/room").status_code == 201
    assert client.post("/v1/scopes/room").status_code == 409
    assert client.post("/v1/scopes/hostname").status_code == 409


@pytest.mark.parametrize(
    "name", ["defaults", "mode", "scope", "suffix", "layers", "Bad Name", "1room", "a/b", "x" * 65]
)
def test_reserved_or_malformed_scope_names_are_refused(client, name):
    response = client.post(f"/v1/scopes/{name}")
    assert response.status_code in (404, 422)
    assert client.get("/v1/scopes").json() == ["hostname", "subject_id"]


def test_created_scopes_survive_a_restart(filesys_store):
    add_scope(filesys_store, "room")
    reopened = FileSysStore(rootdir=filesys_store.rootdir, scopes={"hostname", "subject_id"})
    assert reopened.scope_order == ["hostname", "subject_id", "room"]


def test_add_scope_works_with_both_stores(data_store):
    assert add_scope(data_store, "room") == ["hostname", "subject_id", "room"]
    assert data_store.scope_order == ["hostname", "subject_id", "room"]
    assert "room" in data_store.scopes
    with pytest.raises(ScopeExistsError):
        add_scope(data_store, "room")
