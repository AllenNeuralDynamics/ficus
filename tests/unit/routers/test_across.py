from pathlib import Path

from ficus.services.across import resolve_across


def test_across_scope_works_with_both_stores(data_store):
    items = resolve_across(
        data_store, "software_a", "hostname", "default", ["computer-default-value"]
    )
    assert [item["identifier"] for item in items] == ["w10dtburno", "w11dt000001"]
    assert items[1]["values"]["computer-default-value"] == "to rule them all"


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
