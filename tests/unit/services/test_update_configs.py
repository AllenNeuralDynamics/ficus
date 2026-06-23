import pytest

from ficus.core.exceptions import (
    ConfigNotFoundError,
    ConfigSerializeError,
    InvalidNamespaceError,
    InvalidScopeError,
    InvalidScopeIdentifierError,
    MultipleScopeIdentifiersError
)
from ficus.services.configs import update_config
from pathlib import Path


################################################################################
#
#   update_config()
#
################################################################################


def test_update_config_no_identifier_names_return_data_and_path(data_store):
    namespace = "software_a"
    scope_identifiers = {}
    filename = "config.yml"
    path = data_store.rootdir / Path(f"defaults/{namespace}/{filename}")

    update_data = {"name": "new name", "testing": "ni-haody"}
    result_data, result_path = update_config(data_store=data_store,
                                             namespace=namespace,
                                             filename=filename,
                                             data=update_data,
                                             scope_identifiers=scope_identifiers)
    assert result_data == {
        "name": "new name",  # override
        "scope": "default",  # from defaults/config.yml
        "default-layer-value": "beep beep",  # from defaults/config.yml
        "testing": "ni-haody",
    }
    assert result_path == path


def test_update_config_with_identifier_names_return_data_and_path(data_store):
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001"}
    filename = "config.yml"
    path = data_store.rootdir / Path(f"hostname/{scope_identifiers['hostname']}/{namespace}/{filename}")

    update_data = {"scope": "w11dt000001new", "testing": "ni-haody"}
    result_data, result_path = update_config(data_store=data_store,
                                             namespace=namespace,
                                             filename=filename,
                                             data=update_data,
                                             scope_identifiers=scope_identifiers)
    assert result_data == {
        "scope": "w11dt000001new",  # override
        "computer-layer-value": "boop boop",  # from hostname/w11dt000001/config.yml
        "testing": "ni-haody",
    }
    assert result_path == path


def test_update_config_multi_identifiers_return_multiple_scope_identifiers_error(data_store):
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = "config.yml"
    update_data = {"scope": "w11dt000001new", "testing": "ni-haody"}

    with pytest.raises(MultipleScopeIdentifiersError):
        update_config(data_store=data_store,
                      namespace=namespace,
                      filename=filename,
                      data=update_data,
                      scope_identifiers=scope_identifiers)


def test_update_config_invalid_identifiers_return_invalid_scope_error(data_store):
    namespace = "software_a"
    scope_identifiers = {"fakefake": "w11dt000001"}
    filename = "config.yml"
    update_data = {"scope": "w11dt000001new", "testing": "ni-haody"}

    with pytest.raises(InvalidScopeError):
        update_config(data_store=data_store,
                      namespace=namespace,
                      filename=filename,
                      data=update_data,
                      scope_identifiers=scope_identifiers)


def test_update_config_missing_namespace_return_invalid_namespace_error(data_store):
    namespace = "new_namespace"
    scope_identifiers = {}
    filename="config.yml"
    with pytest.raises(InvalidNamespaceError):
        update_config(data_store=data_store,
                      namespace=namespace,
                      filename=filename,
                      data={},
                      scope_identifiers=scope_identifiers)


def test_update_config_invalid_scope_id_return_invalid_scope_identifier_error(data_store):
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11new"}
    filename="config.yml"
    with pytest.raises(InvalidScopeIdentifierError):
        update_config(data_store=data_store,
                      namespace=namespace,
                      filename=filename,
                      data={},
                      scope_identifiers=scope_identifiers)


def test_update_config_missing_file_return_config_not_found_error(data_store):
    namespace = "software_a"
    scope_identifiers = {}
    filename="config_new.yml"
    with pytest.raises(ConfigNotFoundError):
        update_config(data_store=data_store,
                      namespace=namespace,
                      filename=filename,
                      data={},
                      scope_identifiers=scope_identifiers)


def test_update_config_invalid_data_yaml_return_config_serialize_error(data_store):
    namespace = "software_a"
    scope_identifiers = {}
    filename = "config.yml"
    update_data = {"testing": object()}  # not JSON serializable

    with pytest.raises(ConfigSerializeError):
        update_config(data_store=data_store,
                      namespace=namespace,
                      filename=filename,
                      data=update_data,
                      scope_identifiers=scope_identifiers)


def test_update_config_invalid_data_json_return_config_serialize_error(data_store):
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001"}
    filename = "default.json"
    update_data = {"testing": object()}  # not JSON serializable

    with pytest.raises(ConfigSerializeError):
        update_config(data_store=data_store,
                      namespace=namespace,
                      filename=filename,
                      data=update_data,
                      scope_identifiers=scope_identifiers)
