from ficus.services.configs import get_config
from ficus.services.preview import dry_run_save_config

BASE = "/v1/configs/software_a"


def test_dry_run_does_not_write_to_either_store(data_store):
    current = get_config(data_store, "software_a")
    path = current.override_stack[0]
    original_bytes = data_store.read(path)
    changes = dry_run_save_config(
        data_store,
        namespace="software_a",
        scope_identifiers={},
        data={"default-default-value": "draft"},
        overwrite_defaults=True,
    )
    assert changes[0]["after"]["default-default-value"] == "draft"
    assert data_store.read(path) == original_bytes


def test_preview_merges_draft_without_writing(client):
    current = client.get(BASE).json()["config"]
    path = current["override_stack"][0]
    response = client.post(
        f"{BASE}/preview",
        json={"path": path, "data": {"default-default-value": "draft"}},
    )
    assert response.status_code == 200
    assert response.json()["config"]["data"]["default-default-value"] == "draft"
    assert client.get(BASE).json()["config"] == current


def test_dry_run_save_reports_changes_without_writing(client):
    current = client.get(BASE).json()["config"]
    response = client.post(
        BASE,
        params={"dry_run": "true", "overwrite_defaults": "true"},
        json={"default-default-value": "draft"},
    )
    assert response.status_code == 200
    changes = response.json()["changes"]
    assert any(change["after"]["default-default-value"] == "draft" for change in changes)
    assert client.get(BASE).json()["config"] == current


def test_dry_run_patch_reports_changes_without_writing(client):
    current = client.get(BASE).json()["config"]
    response = client.patch(
        BASE,
        params={"dry_run": "true", "overwrite_defaults": "true"},
        json={"default-default-value": "draft"},
    )
    assert response.status_code == 200
    assert response.json()["changes"]
    assert client.get(BASE).json()["config"] == current


def test_dry_run_can_preview_new_namespace_without_creating_it(client):
    store = client.app.state.data_store
    path = store.rootdir / "defaults" / "new_app"
    response = client.post(
        "/v1/configs/new_app", params={"dry_run": "true"}, json={"new": "value"}
    )
    assert response.status_code == 200
    assert response.json()["changes"][0]["before"] is None
    assert response.json()["changes"][0]["after"] == {"new": "value"}
    assert not store.exists(path)
