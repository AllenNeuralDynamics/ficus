from ficus.services.discovery import list_namespaces, list_scope_identifiers


def test_discovery_across_stores(data_store):
    assert list_namespaces(data_store) == ["software_a", "test_delete_path_error"]
    assert list_scope_identifiers(data_store, "hostname") == ["w10dtburno", "w11dt000001"]
    assert list_scope_identifiers(data_store, "hostname", "software_a") == [
        "w10dtburno", "w11dt000001"
    ]
    assert list_scope_identifiers(data_store, "hostname", "missing") == []


def test_discovery_routes(client):
    assert client.get("/v1/namespaces").json() == ["software_a", "test_delete_path_error"]
    assert client.get("/v1/scopes/subject_id", params={"namespace": "software_a"}).json() == [
        "614173"
    ]
    assert client.get("/v1/scopes/invalid").status_code == 404
