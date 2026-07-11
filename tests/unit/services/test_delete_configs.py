import pytest
from pathlib import Path

from ficus.core.exceptions import (
    ConfigNotFoundError,
    InvalidScopeIdentifierError,
    InvalidNamespaceError,
    InvalidScopeError,
    MultipleScopeIdentifiersError,
)
from ficus.services.configs import delete_config


################################################################################
#
#   delete_config()
#
################################################################################


def test_delete_config_no_identifier_names_return_path(data_store):
    namespace = "software_a"
    scope_identifier = {}
    mode = "config"
    path = data_store.rootdir / Path(f"defaults/{namespace}/{mode}.yml")

    result_path = delete_config(data_store=data_store, namespace=namespace,
                                mode=mode, scope_identifier=scope_identifier)
    assert result_path == str(path)
    assert not data_store.exists(path)



def test_delete_config_with_identifier_names_return_path(data_store):
    namespace = "software_a"
    scope_identifier = {"hostname": "w11dt000001"}
    mode = "config"
    path = data_store.rootdir / Path(f"hostname/{scope_identifier['hostname']}/{namespace}/{mode}.yml")

    result_path = delete_config(data_store=data_store, namespace=namespace,
                                mode=mode, scope_identifier=scope_identifier)
    assert result_path == str(path)
    assert not data_store.exists(path)


def test_delete_config_multi_identifiers_return_multiple_scope_identifiers_error(data_store):
    namespace = "software_a"
    scope_identifier = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"

    with pytest.raises(MultipleScopeIdentifiersError):
        delete_config(data_store=data_store, namespace=namespace, mode=mode,
                      scope_identifier=scope_identifier)


def test_delete_config_invalid_identifier_names_return_invalid_scope_identifier_error(data_store):
    namespace = "software_a"
    scope_identifier = {"fakefake": "value"}
    mode = "config"

    with pytest.raises(InvalidScopeError):
        delete_config(data_store=data_store, namespace=namespace, mode=mode,
                      scope_identifier=scope_identifier)


@pytest.mark.parametrize(
    "namespace, scope_identifier, mode, error_type",
    [
        pytest.param(
            "new_namespace", {}, "config", InvalidNamespaceError, id="missing-namespace"
            ),
        pytest.param(
            "software_a", {}, "config_new", ConfigNotFoundError, id="missing-file"
            ),
        pytest.param(
            "software_a", {"hostname": "w11new"}, "config", InvalidScopeIdentifierError, id="missing-scope-id"
            ),
    ],
)
def test_delete_config_missing_config_return_config_not_found_error(
    data_store, namespace, scope_identifier, mode, error_type
):
    with pytest.raises(error_type):
        delete_config(data_store=data_store, namespace=namespace, mode=mode,
            scope_identifier=scope_identifier)


def test_delete_config_path_is_directory_return_error(data_store):
    """
    This in theory should not happen. API wouldn't allow for the creation of a directory like
    this. However, this could occur if users added nodes with zoonavigator.
    """
    namespace = "test_delete_path_error"
    scope_identifier = {}

    data_store.create(data_store.rootdir / Path(f"defaults/{namespace}/additional_node"), data=None)
    mode = "additional_node"  # this is a directory, not a file

    with pytest.raises(ConfigNotFoundError):
        delete_config(data_store=data_store, namespace=namespace, mode=mode,
                      scope_identifier=scope_identifier)
