import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ficus.routers import router


@pytest.fixture
def client(filesys_store):
    """TestClient wired to a fresh in-memory FileSysStore for every test."""
    app = FastAPI()
    app.state.data_store = filesys_store
    app.include_router(router)
    return TestClient(app)
