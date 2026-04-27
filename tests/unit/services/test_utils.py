import pytest

from ficus.core.exceptions import (
    ConfigSerializeError,
    ConfigDecodeError,
    InvalidScopeIdentifierError,
    UnsupportedFileTypeError,
)
from ficus.services.configs import (
    _deep_update,
    _find_first_invalid_subpath,
    _get_scope_from_identifier_names,
    _validate_and_convert_to_bytes,
    _validate_and_convert_to_dict,
)
from tests.constants import ZK_ROOT_PATH


################################################################################
#
#   _deep_update()
#
################################################################################


def test_deep_update_valid_return_merge():
    original = {"a": 1, "b": 2}
    update = {"b": 3, "c": 4}
    expected_result = {"a": 1, "b": 3, "c": 4}
    assert _deep_update(original, update) == expected_result


def test_merge_configs_override():
    original = {"prime-val": "hello", "scope": "prime"}
    update = {"scope": "mod"}
    expected_result = {"prime-val": "hello", "scope": "mod"}
    assert _deep_update(original, update) == expected_result


def test_merge_configs_append():
    original = {"prime-val": "hello"}
    update = {"mod-val": "world"}
    expected_result = {"prime-val": "hello", "mod-val": "world"}
    assert _deep_update(original, update) == expected_result


@pytest.mark.parametrize(
    "original,update,expected_result",
    [
        pytest.param({"a": 1}, {"a": "2"}, {"a": "2"}, id="int_to_str"),
        pytest.param({"a": "1"}, {"a": 2}, {"a": 2}, id="str_to_int"),
        pytest.param({"a": True}, {"a": None}, {"a": None}, id="bool_to_none"),
        pytest.param({"a": None}, {"a": True}, {"a": True}, id="none_to_bool"),
        pytest.param({"a": "1"}, {"a": 2.0}, {"a": 2.0}, id="str_to_float"),
        pytest.param({"a": "1"}, {"a": b"hi"}, {"a": b"hi"}, id="str_to_bytes"),
    ],
)
def test_deep_update_new_type_return_merge(original, update, expected_result):
    """Test _deep_update where override value has a different type than original value."""
    assert _deep_update(original, update) == expected_result


@pytest.mark.parametrize(
    "original,update,expected_result",
    [
        pytest.param({"a": "str"}, {"a": {}}, {"a": {}}, id="str_to_dict"),
        pytest.param({"a": 1}, {"a": []}, {"a": []}, id="int_to_list"),
        pytest.param({"a": []}, {"a": "str"}, {"a": "str"}, id="list_to_str"),
        pytest.param({"a": []}, {"a": 1}, {"a": 1}, id="list_to_int"),
        pytest.param({"a": {}}, {"a": []}, {"a": []}, id="dict_to_list"),
        pytest.param({"a": []}, {"a": ()}, {"a": ()}, id="list_to_tuple"),
    ],
)
def test_deep_update_collection_type_mismatch_return_merge(original, update, expected_result):
    """Test _deep_update where override value is converting scalar to collection or vice versa."""
    assert _deep_update(original, update) == expected_result


def test_deep_update_nested_dict_return_merge():
    original = {"a": 1, "b": {"test": "value"}}
    update = {"b": {"test": "new_value"}, "c": 4}
    expected_result = {"a": 1, "b": {"test": "new_value"}, "c": 4}
    assert _deep_update(original, update) == expected_result


@pytest.mark.parametrize(
    "original,update,expected_result",
    [
        pytest.param(
            {"a": {"test": {}}}, {"a": {"test": 10}}, {"a": {"test": 10}}, id="dict_to_int"
        ),
        pytest.param(
            {"a": {"test": []}}, {"a": {"test": "1"}}, {"a": {"test": "1"}}, id="list_to_str"
        ),
        pytest.param(
            {"a": {"test": 10}}, {"a": {"test": {}}}, {"a": {"test": {}}}, id="int_to_dict"
        ),
        pytest.param(
            {"a": {"test": "1"}}, {"a": {"test": []}}, {"a": {"test": []}}, id="str_to_list"
        ),
    ],
)
def test_deep_update_nested_dict_new_type_return_merge(original, update, expected_result):
    assert _deep_update(original, update) == expected_result


@pytest.mark.parametrize(
    "original,update,expected_result",
    [
        pytest.param({}, {"b": 3, "c": 4}, {"b": 3, "c": 4}, id="empty-original"),
        pytest.param({"a": 1, "b": 2}, {}, {"a": 1, "b": 2}, id="empty-update"),
        pytest.param({}, {}, {}, id="empty-both"),
    ],
)
def test_deep_update_configs_empty_return_merge(original, update, expected_result):
    assert _deep_update(original, update) == expected_result


################################################################################
#
#   test_validate_and_convert (bytes and dict)
#
################################################################################


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


################################################################################
#
#   test_find_first_invalid_subpath()
#
################################################################################


def test_find_first_invalid_subpath_valid(zk_mock):
    """Test _find_first_invalid_subpath with valid path"""
    path = f"{ZK_ROOT_PATH}/defaults/software_a/config.yml"
    assert _find_first_invalid_subpath(zk_mock, path) is None


def test_find_first_invalid_subpath_invalid_file(zk_mock):
    """Test _find_first_invalid_subpath with invalid file, ignores file check"""
    path = f"{ZK_ROOT_PATH}/defaults/software_a/CONFIG_BAD.yml"
    assert _find_first_invalid_subpath(zk_mock, path, is_file=True) is None


def test_find_first_invalid_subpath_invalid_subpath(zk_mock):
    """Test _find_first_invalid_subpath with invalid subpath (near end)"""
    path = f"{ZK_ROOT_PATH}/defaults/software_a_BAD/CONFIG_BAD.yml"
    assert _find_first_invalid_subpath(zk_mock, path) == f"{ZK_ROOT_PATH}/defaults/software_a_BAD"


def test_find_first_invalid_subpath_invalid_subpath_early(zk_mock):
    """Test _find_first_invalid_subpath with invalid subpath (near beginning)"""
    path = "/scratchbad/defaults/software_a_BAD/CONFIG_BAD.yml"
    assert _find_first_invalid_subpath(zk_mock, path) == "/scratchbad"


################################################################################
#
#   test_get_scope_from_identifier_names()
#
################################################################################


def test_get_scope_from_identifier_names_valid_hostname_return_scopes():
    identifier_names = {"hostname": "w11dt000001"}
    expected_scope = {"computers": "w11dt000001"}
    assert _get_scope_from_identifier_names(identifier_names) == expected_scope


def test_get_scope_from_multi_identifier_names_valid_hostname_return_scopes():
    identifier_names = {"hostname": "w11dt000001", "subject_id": "614173"}
    expected_scope = {"computers": "w11dt000001", "subjects": "614173"}
    assert _get_scope_from_identifier_names(identifier_names) == expected_scope


def test_get_scope_from_identifier_names_invalid_hostname_return_scopes():
    identifier_names = {"unknown-scope": "w11dt000001"}
    with pytest.raises(InvalidScopeIdentifierError):
        _get_scope_from_identifier_names(identifier_names)


def test_get_scope_from_identifier_names_empty_return_empty():
    identifier_names = {}
    assert _get_scope_from_identifier_names(identifier_names) == {}
