import pytest

from ficus.core.exceptions import ConfigSerializeError
from ficus.services.file_crud import create_file, create_file_from_data, delete_file, read_file, read_file_data, update_file_data
from ficus.services.utils import _file_path_from_parts


################################################################################
#
#   read_file()
#
################################################################################


def test_read_file_default_scope_returns_content_and_suffix(data_store):
    content, suffix = read_file(data_store, namespace="software_a")
    assert isinstance(content, str)
    assert suffix == ".yml"


def test_read_file_with_mode_returns_content_and_suffix(data_store):
    content, suffix = read_file(data_store, namespace="software_a", mode="config")
    assert isinstance(content, str)
    assert suffix == ".yml"


def test_read_file_named_scope_returns_content_and_json_suffix(data_store):
    content, suffix = read_file(
        data_store,
        namespace="software_a",
        scope="hostname",
        scope_identifier="w11dt000001",
    )
    assert isinstance(content, str)
    assert suffix == ".json"


def test_read_file_nonexistent_mode_raises_file_not_found_error(data_store):
    with pytest.raises(FileNotFoundError):
        read_file(data_store, namespace="software_a", mode="nonexistent_mode")


def test_read_file_nonexistent_namespace_raises_error(data_store):
    with pytest.raises(Exception):
        read_file(data_store, namespace="nonexistent_namespace")


################################################################################
#
#   create_file()
#
################################################################################


@pytest.mark.parametrize('namespace, mode, scope, scope_identifier, suffix', [
    ("software_a", "new_mode", None, None, ".yml"),
    ("software_a", "new_mode", "hostname", "w11new", ".yml"),
    ("new_namespace", "default", None, None, ".yml"),
])
def test_create_file_uses_right_path(data_store, namespace, mode, scope, scope_identifier, suffix):
    with pytest.raises(FileNotFoundError):
        _file_path_from_parts(
            data_store,
            namespace=namespace,
            mode=mode,
            scope=scope,
            scope_identifier=scope_identifier,
        )
    content = "new_key: new_value\n"
    result = create_file(
        data_store,
        namespace=namespace,
        suffix=suffix,
        mode=mode,
        content=content,
        scope=scope,
        scope_identifier=scope_identifier,
    )
    new_file = _file_path_from_parts(
        data_store,
        namespace=namespace,
        mode=mode,
        scope=scope,
        scope_identifier=scope_identifier,
    )
    assert result == content
    assert data_store.exists(new_file) and new_file.suffix == suffix


def test_create_file_new_mode_in_existing_namespace_returns_content(data_store):
    content = "new_key: new_value\n"
    result = create_file(
        data_store,
        namespace="software_a",
        suffix=".yml",
        mode="new_mode",
        content=content,
    )
    assert result == content


def test_create_file_new_namespace_returns_content(data_store):
    content = "key: value\n"
    result = create_file(
        data_store,
        namespace="new_namespace",
        suffix=".yml",
        mode="default",
        content=content,
    )
    assert result == content


def test_create_file_named_scope_returns_content(data_store):
    content = "host_key: host_value\n"
    result = create_file(
        data_store,
        namespace="software_a",
        suffix=".yml",
        scope="hostname",
        scope_identifier="w11new",
        mode="default",
        content=content,
    )
    assert result == content


def test_create_file_already_exists_raises_file_exists_error(data_store):
    with pytest.raises(FileExistsError):
        create_file(
            data_store,
            namespace="software_a",
            suffix=".yml",
            mode="default",
        )


def test_create_file_overwrite_existing_returns_new_content(data_store):
    content = "overwritten: true\n"
    result = create_file(
        data_store,
        namespace="software_a",
        suffix=".yml",
        mode="default",
        content=content,
        overwrite=True,
    )
    assert result == content


################################################################################
#
#   delete_file()
#
################################################################################


def test_delete_file_default_scope_removes_file(data_store):
    delete_file(data_store, namespace="software_a", mode="config")
    with pytest.raises(FileNotFoundError):
        read_file(data_store, namespace="software_a", mode="config")


def test_delete_file_named_scope_removes_file(data_store):
    delete_file(
        data_store,
        namespace="software_a",
        scope="hostname",
        scope_identifier="w11dt000001",
        mode="config",
    )
    with pytest.raises(FileNotFoundError):
        read_file(
            data_store,
            namespace="software_a",
            scope="hostname",
            scope_identifier="w11dt000001",
            mode="config",
        )


def test_delete_file_nonexistent_mode_raises_file_not_found_error(data_store):
    with pytest.raises(FileNotFoundError):
        delete_file(data_store, namespace="software_a", mode="nonexistent_mode")


################################################################################
#
#   read_file_data()
#
################################################################################


def test_read_file_data_default_scope_returns_dict(data_store):
    result = read_file_data(data_store, namespace="software_a")
    assert isinstance(result, dict)
    assert "default-default-value" in result


def test_read_file_data_with_mode_returns_expected_dict(data_store):
    result = read_file_data(data_store, namespace="software_a", mode="config")
    assert isinstance(result, dict)
    assert result["name"] == "config"


def test_read_file_data_named_scope_returns_dict(data_store):
    result = read_file_data(
        data_store,
        namespace="software_a",
        scope="hostname",
        scope_identifier="w11dt000001",
    )
    assert isinstance(result, dict)
    assert "computer-default-value" in result


def test_read_file_data_nonexistent_mode_raises_file_not_found_error(data_store):
    with pytest.raises(FileNotFoundError):
        read_file_data(data_store, namespace="software_a", mode="nonexistent_mode")


def test_read_file_data_nonexistent_namespace_raises_error(data_store):
    with pytest.raises(Exception):
        read_file_data(data_store, namespace="nonexistent_namespace")


################################################################################
#
#   create_file_from_data()
#
################################################################################


def test_create_file_from_data_new_mode_data_is_readable(data_store):
    data = {"new_key": "new_value"}
    create_file_from_data(
        data_store,
        namespace="software_a",
        data=data,
        suffix=".yml",
        mode="new_mode",
    )
    result = read_file_data(data_store, namespace="software_a", mode="new_mode")
    assert result == data


def test_create_file_from_data_json_suffix_data_is_readable(data_store):
    data = {"json_key": "json_value"}
    create_file_from_data(
        data_store,
        namespace="software_a",
        data=data,
        suffix=".json",
        mode="new_json_mode",
    )
    result = read_file_data(data_store, namespace="software_a", mode="new_json_mode")
    assert result == data


def test_create_file_from_data_named_scope_data_is_readable(data_store):
    data = {"host_key": "host_value"}
    create_file_from_data(
        data_store,
        namespace="software_a",
        data=data,
        suffix=".yml",
        scope="hostname",
        scope_identifier="w11new",
        mode="default",
    )
    result = read_file_data(
        data_store,
        namespace="software_a",
        scope="hostname",
        scope_identifier="w11new",
        mode="default",
    )
    assert result == data


def test_create_file_from_data_already_exists_raises_file_exists_error(data_store):
    with pytest.raises(FileExistsError):
        create_file_from_data(
            data_store,
            namespace="software_a",
            data={"key": "value"},
            suffix=".yml",
            mode="default",
        )


def test_create_file_from_data_overwrite_data_is_readable(data_store):
    data = {"overwritten": True}
    create_file_from_data(
        data_store,
        namespace="software_a",
        data=data,
        suffix=".yml",
        mode="default",
        overwrite=True,
    )
    result = read_file_data(data_store, namespace="software_a", mode="default")
    assert result == data


################################################################################
#
#   update_config()
#
################################################################################


def test_update_config_no_identifier_names_return_data_and_path(data_store):
    namespace = "software_a"
    scope_identifier = {}
    mode = "config"

    update_data = {"name": "new name", "testing": "ni-haody"}
    result_data = update_file_data(
        data_store=data_store,
        namespace=namespace,
        mode=mode,
        data=update_data,
        scope=None,
        scope_identifier=scope_identifier,
    )
    assert result_data == {
        "name": "new name",  # override
        "scope": "default",  # from defaults/config.yml
        "default-layer-value": "beep beep",  # from defaults/config.yml
        "testing": "ni-haody",
    }


def test_update_config_with_identifier_names_return_data_and_path(data_store):
    namespace = "software_a"
    mode = "config"
    update_data = {"scope": "w11dt000001new", "testing": "ni-haody"}
    result_data = update_file_data(
        data_store=data_store,
        namespace=namespace,
        mode=mode,
        data=update_data,
        scope="hostname",
        scope_identifier="w11dt000001",
    )
    assert result_data == {
        "scope": "w11dt000001new",  # override
        "computer-layer-value": "boop boop",  # from hostname/w11dt000001/config.yml
        "testing": "ni-haody",
    }


def test_update_config_invalid_identifiers_return_invalid_scope_error(data_store):
    namespace = "software_a"
    mode = "config"
    update_data = {"scope": "w11dt000001new", "testing": "ni-haody"}

    with pytest.raises(FileNotFoundError):
        update_file_data(
            data_store=data_store,
            namespace=namespace,
            mode=mode,
            data=update_data,
            scope="fakefake",
            scope_identifier="w11dt000001",
        )


def test_update_config_missing_namespace_return_invalid_namespace_error(data_store):
    namespace = "new_namespace"
    mode = "config"
    with pytest.raises(FileNotFoundError):
        update_file_data(
            data_store=data_store,
            namespace=namespace,
            mode=mode,
            data={},
        )


def test_update_config_invalid_scope_id_return_invalid_scope_identifier_error(data_store):
    namespace = "software_a"
    mode = "config"
    with pytest.raises(FileNotFoundError):
        update_file_data(
            data_store=data_store,
            namespace=namespace,
            mode=mode,
            data={},
            scope="hostname",
            scope_identifier="w11new",
        )


def test_update_config_missing_file_return_config_not_found_error(data_store):
    namespace = "software_a"
    mode = "config_new"
    with pytest.raises(FileNotFoundError):
        update_file_data(
            data_store=data_store,
            namespace=namespace,
            mode=mode,
            data={},
        )


def test_update_config_invalid_data_yaml_return_config_serialize_error(data_store):
    namespace = "software_a"
    mode = "config"
    update_data = {"testing": object()}  # not YAML serializable

    with pytest.raises(ConfigSerializeError):
        update_file_data(
            data_store=data_store,
            namespace=namespace,
            mode=mode,
            data=update_data,
        )


def test_update_config_invalid_data_json_return_config_serialize_error(data_store):
    namespace = "software_a"
    mode = "default"
    update_data = {"testing": object()}  # not JSON serializable

    with pytest.raises(ConfigSerializeError):
        update_file_data(
            data_store=data_store,
            namespace=namespace,
            mode=mode,
            data=update_data,
            scope="hostname",
            scope_identifier="w11dt000001",
        )

