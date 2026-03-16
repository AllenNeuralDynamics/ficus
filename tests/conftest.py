import pytest
from fastapi.testclient import TestClient

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
    return FakeZK()


@pytest.fixture(scope="function")
def zk_client(zk_mock):
    app.dependency_overrides[get_zk_client] = lambda: zk_mock
    return TestClient(app)
