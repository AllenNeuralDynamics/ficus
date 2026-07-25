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
    """Client scopes should be a subset of the scopes the server reports."""
    integration_client._validate_scopes()  # raises on mismatch


def test_validate_scopes_superset_raises(ficus_server):
    """Requesting a scope not declared by the server must raise ValueError."""
    integration_client = Confierge(base_url=f"{ficus_server}/v1", scopes={"hostname", "nonexistent"})
    with pytest.raises(ValueError, match="Invalid scopes"):
        integration_client._validate_scopes()


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

