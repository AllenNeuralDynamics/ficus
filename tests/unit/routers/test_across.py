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
