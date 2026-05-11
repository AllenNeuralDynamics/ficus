import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from ficus.main import app
from ficus.database.zookeeper import get_zk_client
from tests.zk_data import FakeZK


################################################################################
#
#   MOCK ZOOKEEPER
#
################################################################################


@pytest.fixture
def zk_mock():
    fake_zk = FakeZK()
    with patch("ficus.services.configs.get_zk_client") as mock_client:
        mock_client.return_value.__enter__.return_value = fake_zk
        yield fake_zk
    


@pytest.fixture(scope="function")
def zk_client(zk_mock):
    app.dependency_overrides[get_zk_client] = lambda: zk_mock
    return TestClient(app)
