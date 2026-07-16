import pytest

from ficus.core.exceptions import (
    ConfigSerializeError,
    ConfigDecodeError,
    UnsupportedFileTypeError,
    InvalidScopeError,
    InvalidNamespaceError,
    InvalidScopeIdentifierError,
)
from ficus.services.utils import (
    _ensure_paths,
    _get_all_search_paths,
    _find_first_invalid_subpath,
    _validate_and_convert_to_bytes,
    _validate_and_convert_to_dict,
    _get_parts_from_path,
)
from ficus.utils.dict_merge import _deep_update, _deep_update_existing_destructive
from pathlib import Path, PurePath


################################################################################
#
#   ensure_paths()
#
################################################################################

def test_ensure_paths_existing_namespace_and_scope_ids(data_store):
    """Existing namespace and scope identifiers are left intact."""
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    paths = _get_all_search_paths(data_store, "software_a", scope_identifiers)
    _ensure_paths(data_store, paths=paths)
    assert data_store.exists(data_store.rootdir / "defaults/software_a")
    assert data_store.exists(data_store.rootdir / "hostname/w11dt000001/software_a")
    assert data_store.exists(data_store.rootdir / "subject_id/614173/software_a")


@pytest.mark.parametrize("namespace, scope_identifiers, kwargs, created_path", [
    ("new_namespace", None,
     {"create_missing_namespace": True},
     "defaults/new_namespace"),
    ("software_a", {"hostname": "new_host"},
     {"create_missing_scope_id": True},
     "hostname/new_host/software_a"),
    ("software_a", {"rig_id": "rig1"},
     {"create_missing_scope": True, "create_missing_scope_id": True},
     "rig_id/rig1/software_a"),
    (None, {"hostname": "new_host"},
     {"create_missing_scope_id": True},
     "hostname/new_host"),
])
def test_ensure_paths_creates_missing(data_store, namespace, scope_identifiers,
                                      kwargs, created_path):
    """Missing namespaces, scopes and scope identifiers are created when the
    corresponding create flags are enabled."""
    path = data_store.rootdir / created_path
    assert not data_store.exists(path)
    paths = _get_all_search_paths(data_store, namespace, scope_identifiers)
    _ensure_paths(data_store, paths=paths, **kwargs)
    assert data_store.exists(path)


@pytest.mark.parametrize("namespace, scope_identifiers, exception", [
    ("does_not_exist", None, InvalidNamespaceError),
    ("software_a", {"hostname": "new_host"}, InvalidScopeIdentifierError),
    ("software_a", {"rig_id": "rig1"}, InvalidScopeError),
])
def test_ensure_paths_raises_when_creation_disabled(data_store, namespace,
                                                    scope_identifiers, exception):
    """Missing structure raises by default since the create flags are disabled."""
    paths = _get_all_search_paths(data_store, namespace, scope_identifiers)
    scopes = set(scope_identifiers.keys()) if scope_identifiers else set()
    with pytest.raises(exception):
        _ensure_paths(data_store, paths=paths, scope_ids_must_exist=scopes)


def test_ensure_paths_all_none_is_noop(data_store):
    """No namespace and no scope identifiers performs no work and does not raise."""
    paths = _get_all_search_paths(data_store, None, None)
    _ensure_paths(data_store, paths=paths)

################################################################################
#
#   _get_all_search_paths()
#
################################################################################

def test_get_all_search_paths_defaults_only(data_store):
    """With no scope identifiers only the defaults namespace path is returned."""
    paths = _get_all_search_paths(data_store, "software_a")
    assert paths == [data_store.rootdir / "defaults/software_a"]


def test_get_all_search_paths_preserves_scope_priority_order(data_store):
    """Paths are returned in merge priority order: defaults first, then scopes
    in the order given by scope_identifiers."""
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    paths = _get_all_search_paths(data_store, "software_a", scope_identifiers)
    assert paths == [
        data_store.rootdir / "defaults/software_a",
        data_store.rootdir / "hostname/w11dt000001/software_a",
        data_store.rootdir / "subject_id/614173/software_a",
    ]


def test_get_all_search_paths_none_scope_identifiers(data_store):
    """Passing None for scope_identifiers behaves like an empty mapping."""
    assert _get_all_search_paths(data_store, "software_a", None) == \
        _get_all_search_paths(data_store, "software_a", {})


def test_get_all_search_paths_none_namespace(data_store):
    """Passing None for namespace behaves like an empty string or default namespace."""
    assert _get_all_search_paths(data_store, None, None) == []


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
    result = _validate_and_convert_to_bytes(PurePath(filename).suffix, data)
    assert isinstance(result, bytes)
    print(result)
    assert result == b'{"key": "value"}'


@pytest.mark.parametrize("filename", ["config.yml", "config.yaml"])
def test_validate_and_convert_to_bytes_valid_yml(filename):
    """Test _validate_and_convert_to_bytes with valid YAML input"""
    data = {"key": "value"}
    result = _validate_and_convert_to_bytes(PurePath(filename).suffix, data)
    assert isinstance(result, bytes)
    print(result)
    assert result == b"key: value\n"


def test_validate_and_convert_to_bytes_invalid_filetype():
    """Test _validate_and_convert_to_bytes with invalid filetype"""
    filename = "config.txt"
    data = {"key": "value"}
    with pytest.raises(UnsupportedFileTypeError):
        _validate_and_convert_to_bytes(PurePath(filename).suffix, data)


def test_validate_and_convert_to_bytes_invalid_data():
    """Test _validate_and_convert_to_bytes with invalid data"""
    filename = "config.yml"
    data = {"key": object()}
    with pytest.raises(ConfigSerializeError):
        _validate_and_convert_to_bytes(PurePath(filename).suffix, data)


def test_validate_and_convert_to_dict_valid_json():
    """Test _validate_and_convert_to_dict with valid JSON input"""
    filename = "config.json"
    data = b'{"key": "value"}'
    result = _validate_and_convert_to_dict(PurePath(filename).suffix, data)
    assert isinstance(result, dict)
    assert result == {"key": "value"}


@pytest.mark.parametrize("filename", ["config.yml", "config.yaml"])
def test_validate_and_convert_to_dict_valid_yml(filename):
    """Test _validate_and_convert_to_dict with valid YAML input"""
    data = b"key: value"
    result = _validate_and_convert_to_dict(PurePath(filename).suffix, data)
    assert isinstance(result, dict)
    assert result == {"key": "value"}


def test_validate_and_convert_to_dict_invalid_filetype():
    """Test _validate_and_convert_to_dict with invalid filetype"""
    filename = "config.txt"
    data = b"asdlfkj"
    with pytest.raises(UnsupportedFileTypeError):
        _validate_and_convert_to_dict(PurePath(filename).suffix, data)


def test_validate_and_convert_to_dict_invalid_data():
    """Test _validate_and_convert_to_dict with invalid data"""
    filename = "config.yml"
    data = b"\x01"
    with pytest.raises(ConfigDecodeError):
        _validate_and_convert_to_dict(PurePath(filename).suffix, data)


def test_validate_and_convert_to_dict_empty_json():
    """Test _validate_and_convert_to_dict with empty json"""
    filename = "config.json"
    data = b"{}"
    data = _validate_and_convert_to_dict(PurePath(filename).suffix, data)
    assert data == {}


def test_validate_and_convert_to_dict_empty_yaml():
    """Test _validate_and_convert_to_dict with empty json"""
    filename = "config.yml"
    data = b""
    data = _validate_and_convert_to_dict(PurePath(filename).suffix, data)
    assert data == {}


################################################################################
#
#   test_find_first_invalid_subpath()
#
################################################################################


def test_find_first_invalid_subpath_valid(data_store):
    """Test _find_first_invalid_subpath with valid path"""
    path = data_store.rootdir / Path("defaults/software_a/config.yml")
    assert _find_first_invalid_subpath(data_store=data_store, path=path) is None


def test_find_first_invalid_subpath_invalid_file(data_store):
    """Test _find_first_invalid_subpath with invalid file, ignores file check"""
    path = data_store.rootdir / Path("defaults/software_a/CONFIG_BAD.yml")
    assert _find_first_invalid_subpath(data_store=data_store, path=path) is None


def test_find_first_invalid_subpath_invalid_subpath(data_store):
    """Test _find_first_invalid_subpath with invalid subpath (near end)"""
    path = data_store.rootdir / Path("defaults/software_a_BAD/CONFIG_BAD.yml")
    assert _find_first_invalid_subpath(data_store=data_store, path=path) == \
        data_store.rootdir / Path("defaults/software_a_BAD")


def test_find_first_invalid_subpath_invalid_subpath_early(data_store):
    """Test _find_first_invalid_subpath with invalid subpath (near beginning)"""
    path = data_store.rootdir / Path("scratchbad/defaults/software_a_BAD/CONFIG_BAD.yml")
    assert _find_first_invalid_subpath(data_store=data_store, path=path) == \
        data_store.rootdir / Path("scratchbad")


def test_find_first_invalid_subpath_invalid_root(data_store):
    """Test _find_first_invalid_subpath with wrong root"""
    path = Path("/scratchbad/defaults/software_a_BAD/CONFIG_BAD.yml") # different root
    assert _find_first_invalid_subpath(data_store=data_store, path=path) == Path("/")

################################################################################
#
#   _get_parts_from_path()
#
################################################################################

@pytest.mark.parametrize("path, expected_namespace, expected_scope_identifiers, expected_filename", [
    (Path("defaults/software_a/config.yml"), "software_a", {}, "config.yml"),
    (Path("hostname/w11dt000001/software_a/config.yml"), "software_a", {"hostname": "w11dt000001"}, "config.yml"),
])
def test_get_parts_from_path(data_store, path, expected_namespace, expected_scope_identifiers, expected_filename):
    namespace, scope_identifier, filename = _get_parts_from_path(data_store=data_store, path=path)
    assert namespace == expected_namespace
    assert scope_identifier == expected_scope_identifiers
    assert filename == expected_filename
