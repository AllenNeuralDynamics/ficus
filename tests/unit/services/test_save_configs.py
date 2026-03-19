import pytest

from ficus.services.configs import get_config, save_config_file, save_config_obj, _save_config

"""
NOTE: Some tests are parameterized to test saving configurations to the following: 
        1. /defaults/... path where default configurations live
        2. /computers/... path where override configurations live
    This is determined by whether a hostname is given or not. 
"""


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test__save_config_existing_namespace(zk_mock, encode_data, hostname):
    """Test saving config file where namespace already exists"""
    namespace = "software_a"  # exists in mock data
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
    """Test saving config file where namespace doesn't exist yet"""
    namespace = "software_test"  # doesn't exist in mock data
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
    """Test saving a default config file (all file types - yml, yaml, json)"""
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
    """Test saving a config file that will override an existing file, when override=True"""
    namespace = "software_a"  # exists in mock data
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
    """Test saving a config - throws errors when saving to an existing file, when override=False"""
    namespace = "software_a"  # exists in mock data
    filename = "config.yml"
    data = {"testing": "ni-haody"}

    with pytest.raises(FileExistsError):
        _save_config(namespace, filename, encode_data(data), hostname)  # Override default to false


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test__save_config_invalid_file_content(zk_mock, hostname):
    """Test _save_config throws an error if data isn't bytes"""
    namespace = "software_a"
    filename = "config.yml"
    data = "not bytes"

    with pytest.raises(TypeError):
        _save_config(namespace, filename, data, hostname, True)


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
@pytest.mark.parametrize("filename", ["default.yml", "default.yaml", "default.json"])
def test__save_config_default_file_exists(zk_mock, encode_data, hostname, filename):
    """Test _save_config throws error when trying to add default file that currently exists (override = False)"""
    namespace = "software_a"
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
    """Test save config (object) with an invalid file content"""
    namespace = "software_test"
    data = {"key": object()}  # python object, invalid for converting to json or yaml

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
    """Test save config (file) with an invalid file content"""
    namespace = "software_test"
    data = b"\x01"  # random byte, fails converting to json or yaml

    with pytest.raises(ValueError):
        save_config_file(namespace, filename, data, hostname)
