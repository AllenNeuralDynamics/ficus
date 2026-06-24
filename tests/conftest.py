import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from tests.zk_data import FakeZK
from tests.zk_data import Node, print_node

from pathlib import Path

from ficus.database.filesys import FileSysStore
from ficus.database.zookeeper import ZKStore
import ficus.database.zookeeper
from ficus.services.configs import _validate_and_convert_to_bytes


# Patch setup_scopes BEFORE any ficus imports trigger it
patch("ficus.database.zookeeper.setup_scopes").start()


@pytest.fixture
def file_structure():
    """Shared recipe for generating fake data store backend for each data store"""
    file_structure = {
        "scratch": {
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
                    "additional_node": {
                        "config.yml": {
                            "name": "config-delete-path-error"
                        }
                    }
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
    }
    return file_structure

@pytest.fixture
def filesys_store(tmp_path, file_structure):
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
                current_path.write_bytes(_validate_and_convert_to_bytes(current_path.suffix,
                                                                        content))

    create_structure(tmp_path, file_structure)
    return FileSysStore(rootdir= tmp_path / "scratch")

@pytest.fixture
def zookeeper_store(monkeypatch, file_structure):

    def make_zk_node(node_name, value: dict | None = None, print_level=0) -> Node:
        """Recursively parse a dict to create ZK Node structure."""
        if node_name.lower().endswith(("yml", "yaml", "json")):
            return Node(name=node_name, value=value)
        children = {}
        if value is None:
            value = {}
        for name, content in value.items():
            children[name] = make_zk_node(node_name=name,
                                          value=content,
                                          print_level=print_level+4)
        return Node(name=node_name, value=None, children=children)

    root = make_zk_node(node_name="root", value=file_structure)
    #print()
    #print_node(root)
    def fake_zk(hosts: list[str]):
        return FakeZK(hosts=hosts, root=root)

    monkeypatch.setattr(ficus.database.zookeeper, "KazooClient", fake_zk)

    zk_store = ZKStore(hosts=["fakehost:9000"], rootdir=Path("scratch"))
    yield zk_store


@pytest.fixture(params=["filesys_store", "zookeeper_store"])
def data_store(request):
    return request.getfixturevalue(request.param)
