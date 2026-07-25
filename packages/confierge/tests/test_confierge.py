"""Unit tests for Confierge — all HTTP calls are intercepted by ``responses``."""
import json

import pytest
import requests
import responses as rsps
from pydantic import BaseModel
from responses import matchers

from confierge import Confierge

BASE_URL = "http://ficus.test/v1"


class SampleModel(BaseModel):
    field1: str
    field2: int


@pytest.fixture
def client():
    return Confierge(base_url=BASE_URL, scopes={"hostname", "subject_id"})


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_init_base_url_from_env(monkeypatch):
    monkeypatch.setenv("FICUS_BASE_URL", "http://env-host/v1")
    assert Confierge().base_url == "http://env-host/v1"


# ---------------------------------------------------------------------------
# _validate_scopes
# ---------------------------------------------------------------------------


@rsps.activate
def test_validate_scopes_valid(client):
    rsps.add(rsps.GET, f"{BASE_URL}/scopes", json=["hostname", "subject_id", "extra"])
    client._validate_scopes()  # subset is fine


@rsps.activate
def test_validate_scopes_unknown_scope_raises(client):
    rsps.add(rsps.GET, f"{BASE_URL}/scopes", json=["hostname"])
    with pytest.raises(ValueError, match="Invalid scopes"):
        client._validate_scopes()


@rsps.activate
def test_validate_scopes_server_error_raises(client):
    rsps.add(rsps.GET, f"{BASE_URL}/scopes", status=500)
    with pytest.raises(requests.HTTPError):
        client._validate_scopes()


# ---------------------------------------------------------------------------
# _cache_file_name — output format and determinism
# ---------------------------------------------------------------------------


def test_cache_file_name_format(client):
    assert client._cache_file_name("ns", "dev.yml", {"b": "2", "a": "1"}) == "ns_a-1_b-2_dev.yml.json"


def test_cache_file_name_scope_order_is_deterministic(client):
    assert (
        client._cache_file_name("ns", "m", {"z": "3", "a": "1"})
        == client._cache_file_name("ns", "m", {"a": "1", "z": "3"})
    )


# ---------------------------------------------------------------------------
# _save_cache / _get_cache / _expire_cache
# ---------------------------------------------------------------------------


def test_save_and_get_cache_roundtrip(tmp_path, client):
    data = {"k": "v"}
    client._save_cache("app", None, None, cache_dir=tmp_path, data=data)
    assert client._get_cache("app", None, None, cache_dir=tmp_path) == data


def test_save_cache_expires_old_file_on_update(tmp_path, client):
    client._save_cache("app", None, None, cache_dir=tmp_path, data={"v": 1})
    client._save_cache("app", None, None, cache_dir=tmp_path, data={"v": 2})
    active = tmp_path / client._cache_file_name("app", None, None)
    assert json.loads(active.read_text()) == {"v": 2}
    assert len(list(tmp_path.iterdir())) == 2  # active + one archived


def test_save_cache_skips_when_data_identical(tmp_path, client):
    data = {"k": "v"}
    client._save_cache("app", None, None, cache_dir=tmp_path, data=data)
    f = tmp_path / client._cache_file_name("app", None, None)
    mtime = f.stat().st_mtime_ns
    client._save_cache("app", None, None, cache_dir=tmp_path, data=data)
    assert f.stat().st_mtime_ns == mtime


# ---------------------------------------------------------------------------
# get_config
# ---------------------------------------------------------------------------


@rsps.activate
def test_get_config_returns_data(client):
    rsps.add(rsps.GET, f"{BASE_URL}/configs/app", json={"config": {"data": {"key": "val"}}})
    assert client.get_config("app") == {"key": "val"}


@rsps.activate
def test_get_config_sends_mode_and_scope_params(client):
    rsps.add(
        rsps.GET,
        f"{BASE_URL}/configs/app",
        json={"config": {"data": {}}},
        match=[matchers.query_param_matcher({"mode": "dev.yml", "hostname": "myhost"})],
    )
    client.get_config("app", mode="dev.yml", scopes={"hostname": "myhost"})


@rsps.activate
def test_get_config_invalid_scope_raises(client):
    with pytest.raises(ValueError, match="Invalid scopes"):
        client.get_config("app", scopes={"unknown_scope": "x"})


@rsps.activate
def test_get_config_http_error_raises(client):
    rsps.add(rsps.GET, f"{BASE_URL}/configs/app", status=404)
    with pytest.raises(requests.HTTPError):
        client.get_config("app")


# ---------------------------------------------------------------------------
# get_config_safe
# ---------------------------------------------------------------------------


@rsps.activate
def test_get_config_safe_returns_validated_model_and_saves_cache(client, tmp_path):
    rsps.add(
        rsps.GET,
        f"{BASE_URL}/configs/app",
        json={"config": {"data": {"field1": "hello", "field2": 42}}},
    )
    result = client.get_config_safe("app", cache_dir=tmp_path, model=SampleModel)
    assert isinstance(result, SampleModel) and result.field1 == "hello"
    assert client._get_cache("app", None, None, cache_dir=tmp_path) == {"field1": "hello", "field2": 42}


def test_get_config_safe_falls_back_to_cache_on_network_error(client, tmp_path):
    client._save_cache("app", None, None, cache_dir=tmp_path, data={"field1": "cached", "field2": 7})
    with rsps.RequestsMock() as rm:
        rm.add(rsps.GET, f"{BASE_URL}/configs/app", body=requests.exceptions.ConnectionError("down"))
        result = client.get_config_safe("app", cache_dir=tmp_path, model=SampleModel)
    assert isinstance(result, SampleModel) and result.field1 == "cached"


def test_get_config_safe_raises_when_no_cache_and_network_error(client, tmp_path):
    with rsps.RequestsMock() as rm:
        rm.add(rsps.GET, f"{BASE_URL}/configs/app", body=requests.exceptions.ConnectionError("down"))
        with pytest.raises(requests.exceptions.ConnectionError):
            client.get_config_safe("app", cache_dir=tmp_path)


# ---------------------------------------------------------------------------
# post_config_file
# ---------------------------------------------------------------------------


@rsps.activate
def test_post_config_file_sends_params(client):
    rsps.add(
        rsps.POST,
        f"{BASE_URL}/configs/app",
        status=201,
        match=[matchers.query_param_matcher({"mode": "dev.yml", "hostname": "myhost"})],
    )
    client.post_config_file("app", {"x": 1}, mode="dev.yml", scopes={"hostname": "myhost"})


@rsps.activate
def test_post_config_file_invalid_scope_raises(client):
    with pytest.raises(ValueError, match="Invalid scopes"):
        client.post_config_file("app", {}, scopes={"bad_scope": "x"})


@rsps.activate
def test_post_config_file_http_error_raises(client):
    rsps.add(rsps.POST, f"{BASE_URL}/configs/app", status=500)
    with pytest.raises(requests.HTTPError):
        client.post_config_file("app", {"x": 1})
