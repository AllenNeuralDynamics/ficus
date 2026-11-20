from fastapi import FastAPI
from fastapi.testclient import TestClient

from ficus.core.proxy import ForwardedPrefixMiddleware


def _client():
    app = FastAPI()
    app.add_middleware(ForwardedPrefixMiddleware)

    @app.get("/v1/ping")
    def ping():
        return {"ok": True}

    return TestClient(app)


def test_without_a_prefix_docs_point_at_the_root():
    client = _client()
    assert client.get("/v1/ping").json() == {"ok": True}
    assert "'/openapi.json'" in client.get("/docs").text


def test_forwarded_prefix_is_used_for_docs_and_servers():
    """Behind a proxy that stripped /canopy/ficus/dev: routes unchanged, links go through it."""
    client = _client()
    headers = {"X-Forwarded-Prefix": "/canopy/ficus/dev/"}
    assert client.get("/v1/ping", headers=headers).json() == {"ok": True}
    assert "'/canopy/ficus/dev/openapi.json'" in client.get("/docs", headers=headers).text
    servers = client.get("/openapi.json", headers=headers).json()["servers"]
    assert servers == [{"url": "/canopy/ficus/dev"}]
