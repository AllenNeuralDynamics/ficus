import pytest

from ficus.core.exceptions import ConfigNotFoundError, ConfigSerializeError, ConfigDecodeError, UnsupportedFileTypeError
from ficus.services.configs import get_config_no_merge, update_config_file, update_config_object

"""
NOTE: Some tests are parameterized to test updating configurations to the following: 
        1. /defaults/... path where default configurations live
        2. /computers/... path where override configurations live
    This is determined by whether a hostname is given or not. 
"""


def test_update_config_obj_defaults(zk_mock):
    """Test updating config file (obj) in /defaults"""
    namespace = "software_a"
    filename = "config.yml"
    hostname = None
    path = f"/scratch/defaults/{namespace}/{filename}"

    data = {"name": "new name", "testing": "ni-haody"}

    new_config_path = update_config_object(namespace, filename, data, hostname)
    new_config = get_config_no_merge(namespace, filename, hostname)

    assert path in new_config_path
    assert new_config[0] == {
        "name": "new name",
        "scope": "default",
        "default-layer-value": "beep beep",
        "testing": "ni-haody",
    }


def test_update_config_obj_computers(zk_mock):
    """Test updating config file (obj) in /computers"""
    namespace = "software_a"
    filename = "config.yml"
    hostname = "w11dt000001"
    path = f"/scratch/computers/{hostname}/{namespace}/{filename}"
    data = {"name": "new name", "testing": "ni-haody"}

    new_config_path = update_config_object(namespace, filename, data, hostname)
    new_config = get_config_no_merge(namespace, filename, hostname)

    assert path in new_config_path
    assert new_config[0] == {
        "name": "new name",
        "scope": "w11dt000001",
        "computer-layer-value": "boop boop",
        "testing": "ni-haody",
    }


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test_update_config_obj_missing_original_file(zk_mock, hostname):
    """Test updating config file (obj) where the original filename doesn't exist"""
    namespace = "software_a"
    filename = "config_doesnt_exist.yml"  # doesn't exist in mock data

    data = {"name": "new name", "testing": "ni-haody"}

    with pytest.raises(ConfigNotFoundError):
        update_config_object(namespace, filename, data, hostname)


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test_update_config_obj_invalid_file_type(zk_mock, hostname):
    """Test updating config file (obj) where the original filename doesn't exist
    Similar test as missing original file since a bad filetype theoretically would never be saved into zookeeper
    """
    namespace = "software_a"
    filename = "config_doesnt_exist.BADBAD"
    data = {"name": "new name", "testing": "ni-haody"}

    with pytest.raises(ConfigNotFoundError):
        update_config_object(namespace, filename, data, hostname)


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test_update_config_obj_invalid_file_content(zk_mock, hostname):
    """Test updating config file (obj) where new data is invalid"""
    namespace = "software_a"
    filename = "config.yml"
    data = {"key": object()}

    with pytest.raises(ConfigSerializeError):
        update_config_object(namespace, filename, data, hostname)


def test_update_config_file_defaults(zk_mock):
    """Test updating config file (file) to /defaults"""
    namespace = "software_a"
    filename = "config.yml"
    input_filename = "different.yml"
    hostname = None
    path = f"/scratch/defaults/{namespace}/{filename}"

    data = b'{"name": "new name", "testing": "ni-haody"}'

    new_config_path = update_config_file(namespace, filename, input_filename, data, hostname)
    new_config = get_config_no_merge(namespace, filename, hostname)

    assert path in new_config_path
    assert new_config[0] == {
        "name": "new name",
        "scope": "default",
        "default-layer-value": "beep beep",
        "testing": "ni-haody",
    }


def test_update_config_file_computers(zk_mock):
    """Test updating config file (file) to /computers"""
    namespace = "software_a"
    filename = "config.yml"
    input_filename = "different.yml"
    hostname = "w11dt000001"
    path = f"/scratch/computers/{hostname}/{namespace}/{filename}"
    data = b'{"name": "new name", "testing": "ni-haody"}'

    new_config_path = update_config_file(namespace, filename, input_filename, data, hostname)
    new_config = get_config_no_merge(namespace, filename, hostname)

    assert path in new_config_path
    assert new_config[0] == {
        "name": "new name",
        "scope": "w11dt000001",
        "computer-layer-value": "boop boop",
        "testing": "ni-haody",
    }


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test_update_config_file_invalid_missing_original_file(zk_mock, hostname):
    """Test updating config file (file) where original filename doesn't exist"""
    namespace = "software_a"
    filename = "config_doesnt_exist.yml"  # doesn't exist in mock data
    input_filename = "config.yml"

    data = b'{"name": "new name", "testing": "ni-haody"}'

    with pytest.raises(ConfigNotFoundError):
        update_config_file(namespace, filename, input_filename, data, hostname)


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test_update_config_file_invalid_file_type(zk_mock, hostname):
    namespace = "software_a"
    filename = "config.yml"
    input_filename = "config.BADDDD"
    data = b'{"name": "new name", "testing": "ni-haody"}'

    with pytest.raises(UnsupportedFileTypeError):
        update_config_file(namespace, filename, input_filename, data, hostname)


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test_update_config_file_invalid_file_content(zk_mock, hostname):
    namespace = "software_a"
    filename = "config.yml"
    input_filename = "config.yml"
    data = b"\x01"

    with pytest.raises(ConfigDecodeError):
        update_config_file(namespace, filename, input_filename, data, hostname)


def test_update_config_file_update_with_yml(zk_mock):
    """Test updating json file with contents from a yaml file"""
    namespace = "software_a"
    filename = "default.json"  # name of file in zookeeper
    input_filename = "config.yml"  # name of file given by user
    hostname = "w11dt000001"
    path = f"/scratch/computers/{hostname}/{namespace}/{filename}"

    # although data is yaml format (would fail for json)
    # still able to update default.json as it converts to python dict
    data = b"name: new name\ntesting: ni-haody"

    new_config_path = update_config_file(namespace, filename, input_filename, data, hostname)
    new_config = get_config_no_merge(namespace, filename, hostname)

    assert path in new_config_path
    assert new_config[0] == {
        "name": "new name",
        "computer-default-value": "to rule them all",
        "testing": "ni-haody",
    }


def test_update_config_file_update_with_json(zk_mock):
    """Test updating yaml file with contents from json file"""
    namespace = "software_a"
    filename = "config.yml"  # name of file in zookeeper
    input_filename = "config.json"  # name of file given by user
    hostname = "w11dt000001"
    path = f"/scratch/computers/{hostname}/{namespace}/{filename}"

    # Data is json format (which means it is valid yaml)
    data = b'{"name": "new name", "testing": "ni-haody"}'

    new_config_path = update_config_file(namespace, filename, input_filename, data, hostname)
    new_config = get_config_no_merge(namespace, filename, hostname)

    assert path in new_config_path
    assert new_config[0] == {
        "name": "new name",
        "scope": "w11dt000001",
        "computer-layer-value": "boop boop",
        "testing": "ni-haody",
    }
