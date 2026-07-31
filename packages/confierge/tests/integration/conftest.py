"""Session-scoped fixture that starts a real Ficus HTTP server backed by a
FileSysStore, so integration tests can hit actual HTTP endpoints instead of
relying on ASGI test transports that bypass the network stack."""
import socket
import threading
import time
from pathlib import Path

from confierge.confierge import Confierge
import pytest
import requests
import uvicorn
from fastapi import FastAPI

from ficus.database.filesys import FileSysStore
from ficus.routers import router as ficus_router
from ficus.services.configs import _validate_and_convert_to_bytes


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _create_filesys_structure(base_path: Path, structure: dict) -> None:
    """Recursively materialise a nested-dict description into real files."""
    for name, content in structure.items():
        current_path = base_path / name
        if isinstance(content, dict) and not name.lower().endswith(("yml", "yaml", "json")):
            current_path.mkdir(parents=True, exist_ok=True)
            _create_filesys_structure(current_path, content)
        else:
            current_path.parent.mkdir(parents=True, exist_ok=True)
            current_path.write_bytes(_validate_and_convert_to_bytes(current_path.suffix, content))


@pytest.fixture(scope="session")
def ficus_server(tmp_path_factory, store_structure):
    """Start a real Ficus HTTP server for the test session.

    Yields the server's base URL (e.g. ``http://127.0.0.1:PORT``).
    The router is mounted at ``/v1``, so full endpoint paths look like
    ``/v1/configs/{namespace}``.
    """
    tmp = tmp_path_factory.mktemp("ficus_store")
    _create_filesys_structure(tmp, store_structure)

    store = FileSysStore(rootdir=tmp / "scratch", scopes={"hostname", "subject_id"})

    app = FastAPI()
    app.state.data_store = store
    app.include_router(ficus_router)

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait up to 5 s for the server to start accepting connections.
    deadline = time.time() + 5.0
    while time.time() < deadline:
        try:
            print(requests.get(f"http://127.0.0.1:{port}/v1/scopes", timeout=0.5))
            break
        except requests.ConnectionError:
            time.sleep(0.05)
    else:
        server.should_exit = True
        raise RuntimeError("Ficus test server did not start within 5 seconds")

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def integration_client(ficus_server, tmp_path) -> Confierge:
    return Confierge(base_url=ficus_server, cache_dir=tmp_path)

