import pytest

from kazoo.exceptions import NoNodeError

from ficus.services.configs import get_all_files, get_all_paths, get_config


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
    """Test namespace/filename that exists but hostname doesn't"""
    with pytest.raises(NoNodeError):
        get_config("software_a", "config.yml", "w11dt000001typo")


def test_get_all_paths(zk_mock):
    namespace = "software_a"
    filename = "config.yml"
    paths = [
        "/scratch/defaults/software_a/config.yml",
        "/scratch/computers/w11dt000001/software_a/config.yml",
    ]

    results = get_all_paths(namespace, filename)

    assert sorted(paths) == sorted(results)


def test_get_all_paths_invalid_namespace(zk_mock):
    namespace = "software_a_fake"
    filename = "config.yml"
    with pytest.raises(NoNodeError):
        get_all_paths(namespace, filename)


def test_get_all_paths_invalid_filename(zk_mock):
    namespace = "software_a"
    filename = "configfakefake.yml"
    with pytest.raises(NoNodeError):
        get_all_paths(namespace, filename)


def test_get_all_files_no_hostname(zk_mock):
    namespace = "software_a"
    files = [
        "/scratch/defaults/software_a/default.yml",
        "/scratch/defaults/software_a/config.yml",
        "/scratch/computers/w11dt000001/software_a/default.json",
        "/scratch/computers/w11dt000001/software_a/config.yml",
        "/scratch/computers/w11dt000002/software_a/default.yaml",
        "/scratch/computers/w11dt000002/software_a/config2.yml",
        "/scratch/computers/w11dt000002/software_a/config3.json",
    ]
    results = get_all_files(namespace)
    assert sorted(files) == sorted(results)


def test_get_all_files_specific_hostname(zk_mock):
    namespace = "software_a"
    hostname = "w11dt000001"
    files = [
        "/scratch/defaults/software_a/default.yml",
        "/scratch/defaults/software_a/config.yml",
        "/scratch/computers/w11dt000001/software_a/default.json",
        "/scratch/computers/w11dt000001/software_a/config.yml",
    ]
    results = get_all_files(namespace, hostname)
    assert sorted(files) == sorted(results)


def test_get_all_files_invalid_namespace(zk_mock):
    namespace = "software_a_fake"
    with pytest.raises(NoNodeError):
        get_all_files(namespace)


def test_get_all_files_invalid_hostname(zk_mock):
    namespace = "software_a"
    hostname = "w11dt000001typo"
    with pytest.raises(NoNodeError):
        get_all_files(namespace, hostname)


# [x] test_get_config
#   - [x] single file (no merge)
#   - [x] default + default.yml
#   - [x] no default + hostname - errors
#   - [x] default + default.yml + hostname + default.yml
#   - [x] invalid namespace
#   - [x] invalid filename
#   - [x] invalid file exists only in default, but tried to look for it in hostname
#   - [x] invalid hostname

# _save_config
#   - [x] valid file
#   - [x] valid hostname
#   - [x] valid default.yml in default
#   - [x] valid default.yml in hostname
#   - [x] valid default (namespace is non-existing)
#   - [x] valid hostname (namespace + hostname is non-existing)
#   - [x] valid override
#   - [x] valid no override
#   - [x] invalid file (unsupported type)
#   - [x] invalid normal already exists - NO OVERRIDE
#   - [x] invalid default already exists (different because checks json,yml,yaml) - NO OVERRIDE

# save_config_obj
#   - [x] test valid - good
#   - [x] invalid file type
#   - [x] invalid file content

# save_config_file
#   - [x] test valid - good
#   - [x] invalid file type
#   - [x] invalid file content

# update_config_obj
#   - [x] merge correct defaults
#   - [x] merge correct computers
#   - [x] invalid file type
#   - [x] invalid file contents (maybe cant for object)
#   - [x] missing current config (namespace,filename) = what is behavior?

# update_config_file
#   - [x] merge correct
#   - [x] invalid file contents (maybe cant for object)
#   - [x] missing current config (namespace,filename) = what is behavior?
#   - [x] partial name mismatched with update config type
#   - [x] partial name bad file type

# delete config
#   - [x] valid default
#   - [x] valid hostname
#   - [x] invalid doesn't exist

# get all paths
#   - [x] valid (check defaults & hostname was found)
#   - [x] invalid namespace
#   - [x] invalid filename

# get all files
#   - [x] valid (check defaults & hostname was found)
#   - [x] invalid namespace
#   - [x] invalid hostname

# _merge_configs
#   - valid two good dicts
#   - valid 1 empty prime (main)
#   - valid 1 empty mod (override)
#   - valid override precedence
#   - valid append new keys
#   - valid nested dict (merge these)
