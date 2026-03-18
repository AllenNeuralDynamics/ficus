import pytest
from kazoo.exceptions import NoNodeError

from ficus.services.configs import get_config


def test_get_config_no_merge_defaults(zk_mock):
    """Grab configs with following behavior:
    - no merging of files (grab filename directly)
    - grab from /defaults directory
    """
    result = get_config("software_a", "config.yml", merge=False)
    assert len(result) == 2
    assert result[0] == {
        "name": "config",
        "scope": "default",
        "default-layer-value": "beep beep",
    }
    assert result[1] == ["/scratch/defaults/software_a/config.yml"]


def test_get_config_no_merge_computers(zk_mock):
    """Grab configs with following behavior:
    - no merging of files (grab filename directly)
    - grab from /computers directory
    - /defaults/<namespace> doesn't exist 
    """
    result = get_config("software_a", "config.yml", "w11dt000001", merge=False)
    assert len(result) == 2
    assert result[0] == {
        "scope": "w11dt000001",
        "computer-layer-value": "boop boop",
    }
    assert result[1] == ["/scratch/computers/w11dt000001/software_a/config.yml"]

def test_get_config_no_merge_computers_no_default(zk_mock):
    """Grab configs with following behavior:
    - no merging of files (grab filename directly)
    - grab from /computers directory
    - /defaults/<namespace> doesn't exist, doesn't matter because we are ignoring merge
    """
    result = get_config("software_b", "config.yml", "w11dt000001", merge=False)
    assert len(result) == 2
    assert result[0] == {
        "scope": "w11dt000001",
        "computer-layer-value": "one one one",
    }
    assert result[1] == ["/scratch/computers/w11dt000001/software_b/config.yml"]


def test_get_config_defaults_default_file(zk_mock):
    """Grab configs with following behavior:
    - merges files (should combine default.yml and <filename>)
    - grab from /defaults directory
    """
    result = get_config("software_a", "config.yml")
    assert len(result) == 2
    assert result[0] == {
        "default-default-value": "the one ring",
        "name": "config",
        "scope": "default",
        "default-layer-value": "beep beep",
    }
    expected = [
        "/scratch/defaults/software_a/default.yml",
        "/scratch/defaults/software_a/config.yml",
    ]
    assert sorted(result[1]) == sorted(expected)


def test_get_config_only_computers(zk_mock):
    """Grab configs with following behavior:
    - <filename> doesn't exist in /defaults path
    - <filename> exists in /computers/<hostname> path
    """
    with pytest.raises(NoNodeError):
        get_config("software_b", "config.yml", "w11dt000001")


def test_get_merge_all(zk_mock):
    """Grabs config merging all relevant files (hostname overrides & default files)"""
    result = get_config("software_a", "config.yml", "w11dt000001")
    assert len(result) == 2
    print(result[0])
    assert result[0] == {
        "default-default-value": "the one ring",  # append from defaults/.../default.yml
        "computer-default-value": "to rule them all",  # append from computers/.../default.json
        "name": "config",  # keep from defaults/.../config.yml
        "default-layer-value": "beep beep",  # keep from defaults/.../config.yml
        "computer-layer-value": "boop boop",  # append from computers/.../config.yml
        "scope": "w11dt000001",  # overridden by computers/.../config.yml
    }
    expected = [
        "/scratch/defaults/software_a/default.yml",
        "/scratch/defaults/software_a/config.yml",
        "/scratch/computers/w11dt000001/software_a/default.json",
        "/scratch/computers/w11dt000001/software_a/config.yml",
    ]
    assert sorted(result[1]) == sorted(expected)


def test_invalid_namespace_defaults(zk_mock):
    """Test namespace that doesn't exist in defaults"""
    with pytest.raises(NoNodeError):
        get_config("software_FAKE", "config.yml")


def test_invalid_filename_defaults(zk_mock):
    """Test namespace that doesn't exist in defaults"""
    with pytest.raises(NoNodeError):
        get_config("software_a", "config_FAKE.yml")


def test_invalid_namespace_hostname(zk_mock):
    """Test namespace/filename that exists in default but not computers/hostname"""
    with pytest.raises(NoNodeError):
        get_config("software_a_default_only", "config.yml", "w11dt000001")


def test_invalid_hostname(zk_mock):
    """Test namespace/filename that exists in but hostname doesn't"""
    with pytest.raises(NoNodeError):
        get_config("software_a", "config.yml", "w11dt000001typo")
