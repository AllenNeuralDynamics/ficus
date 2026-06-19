import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from tests.zk_data import FakeZK

from pathlib import Path

from ficus.database.filesys import FileSysStore
from ficus.database.zookeeper import ZKStore
import ficus.database.zookeeper
from ficus.services.configs import _validate_and_convert_to_bytes


# Patch setup_scopes BEFORE any ficus imports trigger it
patch("ficus.database.zookeeper.setup_scopes").start()


@pytest.fixture
def encode_data():
    def _encode(data: dict) -> bytes:
        return json.dumps(data).encode()

    return _encode


@pytest.fixture(scope="class")
def zk_mock():
    fake_zk = FakeZK()
    with (patch("kazoo.client.KazooClient") as fake_client,):
        fake_client.return_value = fake_zk
        yield fake_zk

    #with (patch("ficus.services.configs.get_zk_client") as mock_svc,):
    #    mock_svc.return_value.__enter__.return_value = fake_zk
    #    yield fake_zk


@pytest.fixture(scope="function")
def zk_client(zk_mock):
    from ficus.main import app

    app.dependency_overrides[get_zk_client] = lambda: zk_mock
    return TestClient(app)


@pytest.fixture
def filesys_store(tmp_path):
    def create_structure(base_path: Path, structure: dict):
        """Recursively parse a dict to create file structure."""
        for name, content in structure.items():
            current_path = base_path / name
            if isinstance(content, dict) and not name.lower().endswith(("yml", "yaml", "json")):
                current_path.mkdir(parents=True, exist_ok=True)
                create_structure(current_path, content)
            else:
                current_path.parent.mkdir(parents=True, exist_ok=True)
                current_path.touch(exist_ok=True)
                current_path.write_bytes(_validate_and_convert_to_bytes(current_path, content))

    file_structure = {
        "defaults": {
            "software_a": {
                "default.yml": {"default-default-value": "the one ring"},
                "config.yml":   {
                    "name": "config",
                    "scope": "default",
                    "default-layer-value": "beep beep"
                }
            },
            # Erroneously created extra folders in default.yml.
            "test_delete_path_error": {
                "additional_node": {}
            }
        },
        "hostname": {
            "w11dt000001": {
                "software_a": {
                    "default.json": {"computer-default-value": "to rule them all"},
                    "config.yml": {"computer-layer-value": "boop boop"}
                }
            }
        },
        "subject_id": {
            "614173": {
                "software_a": {
                    "default.json": {"subject-default-value": "one config to bring them all"},
                    "config.yml": {
                        "subject-layer-value": "bap bap",
                        "scope": "614173",
                        "The Cure": "show me how you do that trick"
                    }
                }
            }
        },
    }

    create_structure(tmp_path, file_structure)

    return FileSysStore(tmp_path)

@pytest.fixture
def zookeeper_store(monkeypatch, tmp_path):
    monkeypatch.setattr(ficus.database.zookeeper, "KazooClient", FakeZK)
    return ZKStore(hosts=["localhost:9000"], rootdir=tmp_path)

#@pytest.fixture(params=["filesys_store", "zookeeper_store"])
@pytest.fixture(params=["filesys_store"])
def data_store(request):
    return request.getfixturevalue(request.param)
