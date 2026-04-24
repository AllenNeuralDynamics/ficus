import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


from ficus.database.zookeeper import get_zk_client
from tests.zk_data import FakeZK


# Patch setup_scopes BEFORE any ficus imports trigger it
patch("ficus.database.zookeeper.setup_scopes").start()


@pytest.fixture
def encode_data():
    def _encode(data: dict) -> bytes:
        return json.dumps(data).encode()

    return _encode


@pytest.fixture
def zk_mock():
    fake_zk = FakeZK()
    with (
        patch("ficus.services.configs.get_zk_client") as mock_svc,
    ):
        mock_svc.return_value.__enter__.return_value = fake_zk
        yield fake_zk


@pytest.fixture(scope="function")
def zk_client(zk_mock):
    from ficus.main import app

    app.dependency_overrides[get_zk_client] = lambda: zk_mock
    return TestClient(app)
