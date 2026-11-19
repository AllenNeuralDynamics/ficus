import copy

import pytest

from ficus.services.inspectors import resolve_across


def test_across_scope_works_with_both_stores(data_store):
    items = resolve_across(
        data_store, "software_a", "hostname", "default", ["computer-default-value"]
    )
    assert [item.identifier for item in items] == ["w10dtburno", "w11dt000001"]
    assert items[1].values["computer-default-value"] == "to rule them all"


def test_across_scope_returns_values_and_sources(client):
    response = client.get(
        "/v1/configs/software_a/across/hostname",
        params={"fields": "default-default-value,computer-default-value,missing"},
    )
    assert response.status_code == 200
    items = {item["identifier"]: item for item in response.json()["items"]}
    assert set(items) == {"w10dtburno", "w11dt000001"}
    rig = items["w11dt000001"]
    assert rig["values"]["computer-default-value"] == "to rule them all"
    assert rig["sources"]["computer-default-value"] == {
        "namespace": "software_a",
        "scope": "hostname",
        "scope_identifier": "w11dt000001",
        "mode": "default",
        "suffix": ".json",
    }
    assert rig["sources"]["default-default-value"]["scope"] is None
    assert rig["values"]["missing"] is None
    assert rig["sources"]["missing"] is None
    assert items["w10dtburno"]["values"]["computer-default-value"] is None


def test_across_scope_returns_all_fields_when_filter_is_omitted(client):
    response = client.get("/v1/configs/software_a/across/subject_id")
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["identifier"] == "614173"
    assert item["values"]["subject-default-value"] == "one config to bring them all"
    source = item["sources"]["subject-default-value"]
    assert (source["scope"], source["scope_identifier"]) == ("subject_id", "614173")


def test_across_scope_rejects_unknown_scope(client):
    assert client.get("/v1/configs/software_a/across/unknown").status_code == 422


def test_across_scope_skips_identifiers_without_the_namespace(client, filesys_store):
    """A rig folder that never runs this namespace is not a row of defaults."""
    filesys_store.create(
        filesys_store.rootdir / "hostname" / "other-rig" / "software_b" / "default.json", b"{}"
    )
    response = client.get(
        "/v1/configs/software_a/across/hostname", params={"fields": "default-default-value"}
    )
    assert response.status_code == 200
    assert [item["identifier"] for item in response.json()["items"]] == [
        "w10dtburno",
        "w11dt000001",
    ]


def test_across_scope_unknown_namespace_is_404(client):
    response = client.get("/v1/configs/no_such_namespace/across/hostname")
    assert response.status_code == 404


def test_across_scope_reports_an_unreadable_leaf_on_its_own_row(client, filesys_store):
    """One rig with a broken leaf gets an error; the others still resolve."""
    broken = filesys_store.rootdir / "hostname" / "w10dtburno" / "software_a" / "default.json"
    filesys_store.create(broken, b"{not json")
    response = client.get(
        "/v1/configs/software_a/across/hostname", params={"fields": "computer-default-value"}
    )
    assert response.status_code == 200
    items = {item["identifier"]: item for item in response.json()["items"]}
    assert items["w10dtburno"]["error"]
    assert items["w10dtburno"]["values"] == {}
    assert items["w10dtburno"]["sources"] == {}
    assert items["w11dt000001"]["error"] is None
    assert items["w11dt000001"]["values"]["computer-default-value"] == "to rule them all"


def test_across_scope_tells_an_explicit_null_from_a_missing_field(client, filesys_store):
    leaf = filesys_store.rootdir / "hostname" / "w11dt000001" / "software_a" / "default.json"
    filesys_store.update(leaf, b'{"computer-default-value": "to rule them all", "cleared": null}')
    response = client.get(
        "/v1/configs/software_a/across/hostname", params={"fields": "cleared,missing"}
    )
    rig = {item["identifier"]: item for item in response.json()["items"]}["w11dt000001"]
    assert rig["values"] == {"cleared": None, "missing": None}
    assert rig["sources"]["cleared"]["scope_identifier"] == "w11dt000001"
    assert rig["sources"]["missing"] is None


@pytest.fixture
def store_structure(store_structure):
    """Adds a nested `camera` block: defaults set both fields, w11dt000001 overrides one."""
    structure = copy.deepcopy(store_structure)
    defaults = structure["scratch"]["defaults"]["software_a"]["default.yml"]
    defaults["camera"] = {"frame_rate": 30, "exposure": 10}
    rig = structure["scratch"]["hostname"]["w11dt000001"]["software_a"]["default.json"]
    rig["camera"] = {"frame_rate": 60}
    return structure


def _where(source):
    """(scope, scope_identifier, suffix) of a source ref; scope is None for defaults."""
    if source is None:
        return None
    if isinstance(source, dict):
        return source["scope"], source["scope_identifier"], source["suffix"]
    return source.scope, source.scope_identifier, source.suffix


RIG = ("hostname", "w11dt000001", ".json")
DEFAULTS = (None, None, ".yml")


def test_across_scope_attributes_each_leaf_of_a_subtree(client):
    response = client.get(
        "/v1/configs/software_a/across/hostname",
        params={"fields": "camera", "identifiers": "w11dt000001"},
    )
    assert response.status_code == 200
    (item,) = response.json()["items"]
    assert item["values"]["camera"] == {"frame_rate": 60, "exposure": 10}
    assert _where(item["sources"]["camera"]) == RIG
    assert _where(item["sources"]["camera.frame_rate"]) == RIG
    assert _where(item["sources"]["camera.exposure"]) == DEFAULTS


def test_across_scope_limits_and_orders_identifiers(client):
    response = client.get(
        "/v1/configs/software_a/across/hostname",
        params={
            "fields": "camera.frame_rate",
            "identifiers": "w11dt000001, w10dtburno,w11dt000001",
        },
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["identifier"] for item in items] == ["w11dt000001", "w10dtburno"]
    assert [item["values"]["camera.frame_rate"] for item in items] == [60, 30]


def test_across_scope_resolves_identifier_without_folder(client):
    response = client.get(
        "/v1/configs/software_a/across/hostname",
        params={"fields": "camera.frame_rate", "identifiers": "new-rig"},
    )
    assert response.status_code == 200
    (item,) = response.json()["items"]
    assert item["identifier"] == "new-rig"
    assert item["values"]["camera.frame_rate"] == 30
    assert _where(item["sources"]["camera.frame_rate"]) == DEFAULTS


def test_across_scope_rejects_unknown_scope_with_identifiers(client):
    response = client.get(
        "/v1/configs/software_a/across/unknown", params={"identifiers": "w11dt000001"}
    )
    assert response.status_code == 422


def test_across_scope_identifiers_work_with_both_stores(data_store):
    items = resolve_across(
        data_store, "software_a", "hostname", "default", ["camera"], ["w11dt000001"]
    )
    assert [item.identifier for item in items] == ["w11dt000001"]
    assert items[0].values["camera"] == {"frame_rate": 60, "exposure": 10}
    assert _where(items[0].sources["camera.frame_rate"]) == RIG
    assert _where(items[0].sources["camera.exposure"]) == DEFAULTS
