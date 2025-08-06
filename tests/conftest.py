# tests/conftest.py
import pytest
import tempfile
from fastapi.testclient import TestClient
from kazoo.exceptions import NoNodeError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock

from calibration_api.database.rigs_pg_db.session import Base, get_db
from calibration_api.main import app
from calibration_api.database.rigs_pg_db.models.rigs import Rigs
from calibration_api.database.rigs_pg_db.models.calibrations import Calibrations
from calibration_api.database.zookeeper.config_server import get_zk_client


################################################################################
#
#   MOCK POSTGRESQL DB
#
################################################################################


@pytest.fixture(scope="session")
def api_prefix():
    return "/api/v1beta"


@pytest.fixture(scope="function")
def db_engine():
    # Create a temp file-based SQLite DB
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    engine = create_engine(
        f"sqlite:///{tmp.name}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
    tmp.close()  # deletes the file


@pytest.fixture(scope="function")
def setup_test_db(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine)
    session = TestingSessionLocal()

    # Seed data once for all tests
 
    session.add(Rigs(rig_name="foo_1_a", rig_type="foo", comp_type="a", instance="1", hostname="w11test-foo", ))
    session.add(Rigs(rig_name="bar_2_b", rig_type="bar", comp_type="b", instance="2", hostname="w11test-bar", ))
    session.commit()

    yield  

    session.close()


@pytest.fixture(scope="function")
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def pg_client(db_session, setup_test_db):
    # Override get_db dependency
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

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
