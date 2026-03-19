import pytest

from ficus.services.configs import get_config, save_config_file, save_config_obj, _save_config


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test__save_config_existing_namespace(zk_mock, encode_data, hostname):
    namespace = "software_a"  # exists in mock data
    if hostname:
        assert zk_mock.exists(f"/scratch/computers/{hostname}/{namespace}")
    assert zk_mock.exists(f"/scratch/defaults/{namespace}")
    filename = "config2.yml"
    if hostname:
        path = f"/scratch/computers/{hostname}/{namespace}/{filename}"
    else:
        path = f"/scratch/defaults/{namespace}/{filename}"
    data = {"testing": "ni-haody"}

    result = _save_config(namespace, filename, encode_data(data), hostname)
    assert result == path

    config = get_config(namespace, filename, hostname, False)
    assert config[0] == data
    assert path in config[1]


@pytest.mark.parametrize("hostname", [None, "w10test"])
def test__save_config_non_existing_namespace(zk_mock, encode_data, hostname):
    """Test saving config file to defaults and computers where namespace doesn't exist yet"""
    namespace = "software_test"  # doesn't exist in mock data
    assert not zk_mock.exists(f"/scratch/computers/{hostname}/{namespace}")
    assert not zk_mock.exists(f"/scratch/defaults/{namespace}")

    filename = "config.yml"
    if hostname:
        # TODO: This is saving a configuration file into a new <hostname> with a new <namespace>.
        # This means a default doesn't exist yet for this <namespace>. Should we allow users to save a new <hostname>
        # if a default hasn't been given yet? Ask this because behavior of "get_config" is to error when no default
        # is given, regardless if hostname override exists. However, doing no merge will allow you to grab file.
        # Current assumption is user allowed to create <hostname>/<namespace> regardless of default/<namespace> existing
        path = f"/scratch/computers/{hostname}/{namespace}/{filename}"
    else:
        path = f"/scratch/defaults/{namespace}/{filename}"
    data = {"testing": "ni-haody"}

    result = _save_config(namespace, filename, encode_data(data), hostname)
    assert result == path

    config = get_config(namespace, filename, hostname, False)
    assert config[0] == data
    assert path in config[1]


@pytest.mark.parametrize("hostname", [None, "w10test"])
@pytest.mark.parametrize("filename", ["default.yml", "default.yaml", "default.json"])
def test__save_config_default_file(zk_mock, encode_data, filename, hostname):
    """Test saving a default config file (all file types - yml,yaml,json) to both defaults and computers"""
    namespace = "software_test"
    if hostname:
        path = f"/scratch/computers/{hostname}/{namespace}/{filename}"
    else:
        path = f"/scratch/defaults/{namespace}/{filename}"
    data = {"testing": "ni-haody"}

    result = _save_config(namespace, filename, encode_data(data), hostname)
    assert result == path

    config = get_config(namespace, filename, hostname, False)
    assert config[0] == data
    assert path in config[1]


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test__save_config_override(zk_mock, encode_data, hostname):
    """Test that config exists in defaults/hostname override and can still save config if override is True"""
    namespace = "software_a"  # exists in mock data
    if hostname:
        assert zk_mock.exists(f"/scratch/computers/{hostname}/{namespace}")
    assert zk_mock.exists(f"/scratch/defaults/{namespace}")
    filename = "config.yml"
    if hostname:
        path = f"/scratch/computers/{hostname}/{namespace}/{filename}"
    else:
        path = f"/scratch/defaults/{namespace}/{filename}"
    data = {"testing": "ni-haody"}

    current_config = get_config(namespace, filename, hostname, False)

    result = _save_config(namespace, filename, encode_data(data), hostname, True)
    assert result == path

    new_config = get_config(namespace, filename, hostname, False)
    assert new_config[0] == data
    assert path in new_config[1]
    assert current_config != new_config


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test__save_config_no_override_file_exists(zk_mock, hostname, encode_data):
    """Test that config exists in defaults/hostname override and can't override when override is False"""
    namespace = "software_a"  # exists in mock data
    if hostname:
        assert zk_mock.exists(f"/scratch/computers/{hostname}/{namespace}")
    assert zk_mock.exists(f"/scratch/defaults/{namespace}")
    filename = "config.yml"
    data = {"testing": "ni-haody"}

    with pytest.raises(FileExistsError):
        _save_config(namespace, filename, encode_data(data), hostname)  # Override default to false


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test__save_config_invalid_file_content(zk_mock, hostname):
    """Test throwing error if data isn't bytes"""
    namespace = "software_a"
    filename = "config.yml"
    data = "not bytes"

    with pytest.raises(TypeError):
        _save_config(namespace, filename, data, hostname, True)


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test__save_config_file_exists(zk_mock, encode_data, hostname):
    """Test error occurs when trying to add file that currently exists (with override = False)"""
    namespace = "software_a"
    filename = "config.yml"
    if hostname:
        assert zk_mock.exists(f"/scratch/computers/{hostname}/{namespace}/{filename}")
    assert zk_mock.exists(f"/scratch/defaults/{namespace}/{filename}")
    data = {"testing": "ni-haody"}

    with pytest.raises(FileExistsError):
        _save_config(namespace, filename, encode_data(data), hostname)


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
@pytest.mark.parametrize("filename", ["default.yml", "default.yaml", "default.json"])
def test__save_config_default_file_exists(zk_mock, encode_data, hostname, filename):
    """Test error occurs when trying to add file that currently exists (with override = False)"""
    namespace = "software_a"
    if hostname:
        assert zk_mock.exists(f"/scratch/computers/{hostname}/{namespace}/default.json")
    assert zk_mock.exists(f"/scratch/defaults/{namespace}/default.yml")
    data = {"testing": "ni-haody"}

    with pytest.raises(FileExistsError):
        _save_config(namespace, filename, encode_data(data), hostname)


@pytest.mark.parametrize("hostname", [None, "w10test"])
def test_save_config_obj(zk_mock, hostname):
    """Test save config (object)"""
    namespace = "software_test"
    filename = "config.yml"
    if hostname:
        path = f"/scratch/computers/{hostname}/{namespace}/{filename}"
    else:
        path = f"/scratch/defaults/{namespace}/{filename}"
    data = {"testing": "ni-haody"}

    result = save_config_obj(namespace, filename, data, hostname)
    assert result == path


@pytest.mark.parametrize("hostname", [None, "w10test"])
def test_save_config_obj_invalid_file_type(zk_mock, hostname):
    """Test save config (object) with an invalid file type"""
    namespace = "software_test"
    filename = "config.BADBAD"
    data = {"testing": "ni-haody"}

    with pytest.raises(ValueError):
        save_config_obj(namespace, filename, data, hostname)


@pytest.mark.parametrize("hostname", [None, "w10test"])
@pytest.mark.parametrize("filename", ["default.yml", "default.yaml", "default.json"])
def test_save_config_obj_invalid_file_content(zk_mock, filename, hostname):
    """Test save config (object) with an invalid file content (dictionary contains object - fails for yaml and json)"""
    namespace = "software_test"
    data = {"key": object()}

    with pytest.raises(ValueError):
        save_config_obj(namespace, filename, data, hostname)


@pytest.mark.parametrize("hostname", [None, "w10test"])
def test_save_config_file(zk_mock, hostname):
    """Test save config (file)"""
    namespace = "software_test"
    filename = "config.yml"
    if hostname:
        path = f"/scratch/computers/{hostname}/{namespace}/{filename}"
    else:
        path = f"/scratch/defaults/{namespace}/{filename}"
    data = b"testing: ni-haody"

    result = save_config_file(namespace, filename, data, hostname)
    assert result == path


@pytest.mark.parametrize("hostname", [None, "w10test"])
def test_save_config_file_invalid_file_type(zk_mock, hostname):
    """Test save config (file) with an invalid file type"""
    namespace = "software_test"
    filename = "config.BADBAD"
    data = b"testing: ni-haody"

    with pytest.raises(ValueError):
        save_config_obj(namespace, filename, data, hostname)


@pytest.mark.parametrize("hostname", [None, "w10test"])
@pytest.mark.parametrize("filename", ["default.yml", "default.yaml", "default.json"])
def test_save_config_file_invalid_file_content(zk_mock, filename, hostname):
    """Test save config (file) with an invalid file content (dictionary contains object - fails for yaml and json)"""
    namespace = "software_test"
    data = b"\x01"

    with pytest.raises(ValueError):
        save_config_file(namespace, filename, data, hostname)


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
#   - merge correct
#   - invalid file type
#   - invalid file contents (maybe cant for object)
#   - missing current config (namespace,filename) = what is behavior?
#   - invalid partial_filename = what is behavior?

# update_config_file
#   - merge correct
#   - invalid file type
#   - invalid file contents (maybe cant for object)
#   - missing current config (namespace,filename) = what is behavior?
#   - invalid partial_filename = what is behavior?

# delete config
#   - valid default
#   - valid hostname
#   - invalid doesn't exist

# get all paths
#   - valid (check defaults & hostname was found)
#   - invalid namespace
#   - invalid filename

# get all paths
#   - valid (check defaults & hostname was found)
#   - invalid namespace
#   - invalid hostname

# _merge_configs
#   - valid two good dicts
#   - valid 1 empty prime (main)
#   - valid 1 empty mod (override)
#   - valid override precedence
#   - valid append new keys
#   - valid nested dict (merge these)
