import pytest

from ficus.core.exceptions import ConfigSerializeError, ConfigDecodeError, UnsupportedFileTypeError
from ficus.services.configs import (
    _merge_configs,
    _validate_and_convert_to_bytes,
    _validate_and_convert_to_dict,
    _find_first_invalid_subpath,
)


def test_merge_configs_valid():
    """Test _merge_configs with valid input"""
    prime_dict = {"a": 1, "b": 2}
    mod_dict = {"b": 3, "c": 4}
    expected_result = {"a": 1, "b": 3, "c": 4}
    assert _merge_configs(prime_dict, mod_dict) == expected_result


@pytest.mark.parametrize(
    "prime_dict,mod_dict,expected",
    [
        ({}, {"b": 3, "c": 4}, {"b": 3, "c": 4}),
        ({"a": 1, "b": 2}, {}, {"a": 1, "b": 2}),
        ({}, {}, {}),
    ],
)
def test_merge_configs_empty(prime_dict, mod_dict, expected):
    """Test _merge_configs with empty dictionaries"""
    assert _merge_configs(prime_dict, mod_dict) == expected


def test_merge_configs_override():
    """Test _merge_configs where mod_dict overrides prime_dict"""
    prime_dict = {"prime-val": "hello", "scope": "prime"}
    mod_dict = {"scope": "mod"}
    expected = {"prime-val": "hello", "scope": "mod"}
    assert _merge_configs(prime_dict, mod_dict) == expected


def test_merge_configs_append():
    """Test _merge_configs where mod_dict appends to prime_dict"""
    prime_dict = {"prime-val": "hello"}
    mod_dict = {"mod-val": "world"}
    expected = {"prime-val": "hello", "mod-val": "world"}
    assert _merge_configs(prime_dict, mod_dict) == expected


def test_merge_configs_nested_override():
    """Test _merge_configs with nested dictionaries where mod_dict overrides prime_dict"""
    prime_dict = {"scope": {"hello": "world", "scope": "prime"}}
    mod_dict = {"scope": {"scope": "mod"}}
    expected = {"scope": {"hello": "world", "scope": "mod"}}
    assert _merge_configs(prime_dict, mod_dict) == expected


def test_merge_configs_nested_append():
    """Test _merge_configs with nested dictionaries where mod_dict appends to prime_dict"""
    prime_dict = {"scope": {"hello": "world"}}
    mod_dict = {"scope": {"beep": "boop"}}
    expected = {"scope": {"hello": "world", "beep": "boop"}}
    assert _merge_configs(prime_dict, mod_dict) == expected


def test_validate_and_convert_to_bytes_valid_json():
    """Test _validate_and_convert_to_bytes with valid JSON input"""
    filename = "config.json"
    data = {"key": "value"}
    result = _validate_and_convert_to_bytes(filename, data)
    assert isinstance(result, bytes)
    print(result)
    assert result == b'{"key": "value"}'


@pytest.mark.parametrize("filename", ["config.yml", "config.yaml"])
def test_validate_and_convert_to_bytes_valid_yml(filename):
    """Test _validate_and_convert_to_bytes with valid YAML input"""
    data = {"key": "value"}
    result = _validate_and_convert_to_bytes(filename, data)
    assert isinstance(result, bytes)
    print(result)
    assert result == b"key: value\n"


def test_validate_and_convert_to_bytes_invalid_filetype():
    """Test _validate_and_convert_to_bytes with invalid filetype"""
    filename = "config.txt"
    data = {"key": "value"}
    with pytest.raises(UnsupportedFileTypeError):
        _validate_and_convert_to_bytes(filename, data)


def test_validate_and_convert_to_bytes_invalid_data():
    """Test _validate_and_convert_to_bytes with invalid data"""
    filename = "config.yml"
    data = {"key": object()}
    with pytest.raises(ConfigSerializeError):
        _validate_and_convert_to_bytes(filename, data)


def test_validate_and_convert_to_dict_valid_json():
    """Test _validate_and_convert_to_dict with valid JSON input"""
    filename = "config.json"
    data = b'{"key": "value"}'
    result = _validate_and_convert_to_dict(filename, data)
    assert isinstance(result, dict)
    assert result == {"key": "value"}


@pytest.mark.parametrize("filename", ["config.yml", "config.yaml"])
def test_validate_and_convert_to_dict_valid_yml(filename):
    """Test _validate_and_convert_to_dict with valid YAML input"""
    data = b"key: value"
    result = _validate_and_convert_to_dict(filename, data)
    assert isinstance(result, dict)
    assert result == {"key": "value"}


def test_validate_and_convert_to_dict_invalid_filetype():
    """Test _validate_and_convert_to_dict with invalid filetype"""
    filename = "config.txt"
    data = b"asdlfkj"
    with pytest.raises(UnsupportedFileTypeError):
        _validate_and_convert_to_dict(filename, data)


def test_validate_and_convert_to_dict_invalid_data():
    """Test _validate_and_convert_to_dict with invalid data"""
    filename = "config.yml"
    data = b"\x01"
    with pytest.raises(ConfigDecodeError):
        _validate_and_convert_to_dict(filename, data)


def test_validate_and_convert_to_dict_empty_json():
    """Test _validate_and_convert_to_dict with empty json"""
    filename = "config.json"
    data = b"{}"
    data = _validate_and_convert_to_dict(filename, data)
    assert data == {}


def test_validate_and_convert_to_dict_empty_yaml():
    """Test _validate_and_convert_to_dict with empty json"""
    filename = "config.yml"
    data = b""
    data = _validate_and_convert_to_dict(filename, data)
    assert data == {}


def test_find_first_invalid_subpath_valid(zk_mock):
    """Test _find_first_invalid_subpath with valid path"""
    path = "/scratch/defaults/software_a/config.yml"
    assert _find_first_invalid_subpath(zk_mock, path) is None


def test_find_first_invalid_subpath_invalid_file(zk_mock):
    """Test _find_first_invalid_subpath with invalid file, ignores file check"""
    path = "/scratch/defaults/software_a/CONFIG_BAD.yml"
    assert _find_first_invalid_subpath(zk_mock, path, is_file=True) is None


def test_find_first_invalid_subpath_invalid_subpath(zk_mock):
    """Test _find_first_invalid_subpath with invalid subpath (near end)"""
    path = "/scratch/defaults/software_a_BAD/CONFIG_BAD.yml"
    assert _find_first_invalid_subpath(zk_mock, path) == "/scratch/defaults/software_a_BAD"


def test_find_first_invalid_subpath_invalid_subpath_early(zk_mock):
    """Test _find_first_invalid_subpath with invalid subpath (near beginning)"""
    path = "/scratchbad/defaults/software_a_BAD/CONFIG_BAD.yml"
    assert _find_first_invalid_subpath(zk_mock, path) == "/scratchbad"
