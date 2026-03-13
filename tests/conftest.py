# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from kazoo.exceptions import NoNodeError
from unittest.mock import MagicMock

from ficus.main import app
from ficus.database.zookeeper import get_zk_client


################################################################################
#
#   MOCK ZOOKEEPER
#
################################################################################


@pytest.fixture
def zk_mock():
    zk = MagicMock()
    def get_side_effect(path):
        if path == "/projects/test_project/defaults/configuration":
            return (b"test_key_default: test_value_default", None)
        elif path == "/rigs/test_rig/projects/test_project/configuration":
            return (b"test_key_rig: test_value_rig", None) 
        else:
            raise NoNodeError()
    zk.get.side_effect = get_side_effect
    return zk


@pytest.fixture(scope="function")
def zk_client(zk_mock):

    app.dependency_overrides[get_zk_client] = lambda: zk_mock
    return TestClient(app)
