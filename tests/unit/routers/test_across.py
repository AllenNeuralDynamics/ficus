import copy

import pytest
from pathlib import Path

from ficus.services.across import resolve_across


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
    assert Path(rig["sources"]["computer-default-value"]).parts[-4:] == (
        "hostname", "w11dt000001", "software_a", "default.json"
    )
    assert rig["values"]["missing"] is None
    assert rig["sources"]["missing"] is None
    assert items["w10dtburno"]["values"]["computer-default-value"] is None


def test_across_scope_returns_all_fields_when_filter_is_omitted(client):
    response = client.get("/v1/configs/software_a/across/subject_id")
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["identifier"] == "614173"
    assert item["values"]["subject-default-value"] == "one config to bring them all"
    assert Path(item["sources"]["subject-default-value"]).parts[-4:] == (
        "subject_id", "614173", "software_a", "default.json"
    )


def test_across_scope_rejects_unknown_scope(client):
    assert client.get("/v1/configs/software_a/across/unknown").status_code == 422


@pytest.fixture
def store_structure(store_structure):
    """Adds a nested `camera` block: defaults set both fields, w11dt000001 overrides one."""
    structure = copy.deepcopy(store_structure)
    defaults = structure["scratch"]["defaults"]["software_a"]["default.yml"]
    defaults["camera"] = {"frame_rate": 30, "exposure": 10}
    rig = structure["scratch"]["hostname"]["w11dt000001"]["software_a"]["default.json"]
    rig["camera"] = {"frame_rate": 60}
    return structure


def _file(source):
    return Path(source).parts[-4:] if source else None


def test_across_scope_attributes_each_leaf_of_a_subtree(client):
    response = client.get(
        "/v1/configs/software_a/across/hostname",
        params={"fields": "camera", "identifiers": "w11dt000001"},
    )
    assert response.status_code == 200
    (item,) = response.json()["items"]
    assert item["values"]["camera"] == {"frame_rate": 60, "exposure": 10}
    rig_file = ("hostname", "w11dt000001", "software_a", "default.json")
    assert _file(item["sources"]["camera"]) == rig_file
    assert _file(item["sources"]["camera.frame_rate"]) == rig_file
    assert Path(item["sources"]["camera.exposure"]).parts[-3:] == (
        "defaults", "software_a", "default.yml"
    )


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
    assert Path(item["sources"]["camera.frame_rate"]).parts[-3:] == (
        "defaults", "software_a", "default.yml"
    )


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
    assert _file(items[0].sources["camera.frame_rate"])[0] == "hostname"
    assert Path(items[0].sources["camera.exposure"]).parts[-3] == "defaults"
