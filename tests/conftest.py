# tests/conftest.py
import pytest
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from calibration_api.database.session import Base, get_db
from calibration_api.main import app
from calibration_api.database.models.rigs import Rigs
from calibration_api.database.models.calibrations import Calibrations

@pytest.fixture(scope="session")
def db_engine():
    # Create a temp file-based SQLite DB
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    engine = create_engine(
        f"sqlite:///{tmp.name}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    tmp.close()  # deletes the file

@pytest.fixture()
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture()
def client(db_session):
    # Override get_db dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
