from ficus.core.config import Settings, settings
from ficus.main import app


def test_cors_origins_can_be_configured_from_environment(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["https://ficus-tree.example"]')
    assert Settings().cors_origins == ["https://ficus-tree.example"]


def test_cors_middleware_uses_configured_origins():
    middleware = next(m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware")
    assert middleware.kwargs["allow_origins"] == settings.cors_origins
    assert middleware.kwargs["allow_methods"] == ["GET", "POST", "PATCH", "DELETE"]
    assert middleware.kwargs["allow_headers"] == ["Content-Type"]
