import pytest
from pydantic import ValidationError

from ficus.core.config import Settings


@pytest.fixture(autouse=True)
def no_ficus_env(monkeypatch, tmp_path):
    """Settings from these tests' env only: no .env, no stray deployment variables."""
    monkeypatch.chdir(tmp_path)
    for name in ("ZK_HOSTS", "ZK_HOST", "HOST", "ZK_TIMEOUT", "ROOT_PATH", "API_NAME", "LOG_LEVEL"):
        monkeypatch.delenv(name, raising=False)


def test_defaults():
    settings = Settings()
    assert settings.zk_hosts == ["eng-logtools:2181"]
    assert settings.zk_timeout == 15.0
    assert settings.root_path == ""
    assert settings.log_level == "INFO"


@pytest.mark.parametrize(
    "value", ["zk1:2181, zk2:2181", '["zk1:2181", "zk2:2181"]']
)
def test_zk_hosts_from_env_comma_separated_or_json(monkeypatch, value):
    monkeypatch.setenv("ZK_HOSTS", value)
    assert Settings().zk_hosts == ["zk1:2181", "zk2:2181"]


def test_zk_hosts_accepts_the_older_name(monkeypatch):
    monkeypatch.setenv("ZK_HOST", "zk1:2181")
    assert Settings().zk_hosts == ["zk1:2181"]


def test_zk_hosts_wins_over_the_older_name(monkeypatch):
    monkeypatch.setenv("ZK_HOST", "old:2181")
    monkeypatch.setenv("ZK_HOSTS", "new:2181")
    assert Settings().zk_hosts == ["new:2181"]


def test_zk_hosts_ignores_a_generic_host_variable(monkeypatch):
    """HOST is often the bind address (HOST=0.0.0.0), not ZooKeeper."""
    monkeypatch.setenv("HOST", "0.0.0.0")
    assert Settings().zk_hosts == ["eng-logtools:2181"]


@pytest.mark.parametrize(
    "name,value,expected",
    [
        ("ROOT_PATH", "canopy/ficus/dev", "/canopy/ficus/dev"),
        ("ROOT_PATH", "/ficus/", "/ficus"),
        ("ROOT_PATH", "/", ""),
        ("API_NAME", "ficus-dev", "/ficus-dev"),
    ],
)
def test_root_path_is_normalized(monkeypatch, name, value, expected):
    monkeypatch.setenv(name, value)
    assert Settings().root_path == expected


def test_env_values(monkeypatch):
    monkeypatch.setenv("ZK_TIMEOUT", "2.5")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    settings = Settings()
    assert settings.zk_timeout == 2.5
    assert settings.log_level == "DEBUG"


@pytest.mark.parametrize("name,value", [("ZK_TIMEOUT", "0"), ("LOG_LEVEL", "LOUD")])
def test_rejects_bad_values(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        Settings()


def test_env_example_parses(monkeypatch):
    """Every line of .env.example is a valid setting, and they're the defaults."""
    from pathlib import Path

    example = Path(__file__).parents[2] / ".env.example"
    assert Settings(_env_file=example).model_dump() == Settings().model_dump()

def test_scopes_keep_their_order():
    assert Settings().scopes == ["hostname", "subject_id"]
    assert Settings(scopes=["subject_id", "hostname"]).scopes == ["subject_id", "hostname"]


@pytest.mark.parametrize("scopes", [["hostname", "hostname"], ["mode"]])
def test_scopes_reject_duplicates_and_mode(scopes):
    with pytest.raises(ValidationError):
        Settings(scopes=scopes)
