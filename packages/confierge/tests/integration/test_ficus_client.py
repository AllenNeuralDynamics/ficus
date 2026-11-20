"""Integration tests: FicusClient against a real (in-process) Ficus server.

Run with:
    pytest -m integration
"""
import requests
import pytest

from confierge import Confierge

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# /v1/scopes 
# ---------------------------------------------------------------------------


def test_validate_scopes(integration_client: Confierge):
    """Known scopes should be accepted without raising."""
    integration_client.validate_scopes({"hostname"})  # raises on mismatch


def test_validate_scopes_superset_raises(ficus_server, tmp_path):
    """Requesting a scope not declared by the server must raise ValueError."""
    client = Confierge(base_url=ficus_server, cache_dir=tmp_path)
    with pytest.raises(ValueError, match="Invalid scopes"):
        client.validate_scopes({"hostname", "nonexistent"})


# ---------------------------------------------------------------------------
# get_config
# ---------------------------------------------------------------------------


def test_get_config_default(integration_client: Confierge):
    """Default merged config should include values from the defaults layer."""
    result = integration_client.get_config("software_a", mode="config")
    assert isinstance(result, dict)
    assert "default-layer-value" in result


def test_get_config_with_hostname_scope(integration_client: Confierge):
    """Config merged with a hostname scope should include computer-layer values."""
    result = integration_client.get_config(
        "software_a",
        mode="config",
        scopes={"hostname": "w11dt000001"},
    )
    assert "computer-layer-value" in result


def test_get_config_with_subject_scope(integration_client: Confierge):
    """Config merged with a subject_id scope should include subject-layer values."""
    result = integration_client.get_config(
        "software_a",
        mode="config",
        scopes={"subject_id": "614173"},
    )
    assert "subject-layer-value" in result


def test_get_config_not_found_raises(integration_client: Confierge):
    """Requesting a namespace that does not exist should raise an HTTP error."""
    with pytest.raises(requests.HTTPError, match="404"):
        integration_client.get_config("nonexistent_namespace")



# ---------------------------------------------------------------------------
# POST /v1/configs/{namespace}: create_if_missing reaches Ficus
# ---------------------------------------------------------------------------

def test_post_config_file_refuses_a_new_namespace_by_default(integration_client: Confierge):
    with pytest.raises(requests.HTTPError):
        integration_client.post_config_file("confierge_absent_ns", {"a": 1})
    with pytest.raises(requests.HTTPError):
        integration_client.get_config("confierge_absent_ns")


def test_post_config_file_creates_a_namespace_when_asked(integration_client: Confierge):
    integration_client.post_config_file("confierge_new_ns", {"a": 1}, create_if_missing=True)
    assert integration_client.get_config("confierge_new_ns") == {"a": 1}
