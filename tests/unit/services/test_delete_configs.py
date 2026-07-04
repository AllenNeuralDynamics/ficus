import pytest
from pathlib import Path

from ficus.core.exceptions import (
    ConfigNotFoundError,
    InvalidScopeIdentifierError,
    PathIsDirectoryError,
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
    filename = "config.yml"
    path = data_store.rootdir / Path(f"defaults/{namespace}/{filename}")

    result_path = delete_config(data_store=data_store, namespace=namespace,
                                filename=filename, scope_identifier=scope_identifier)
    assert result_path == str(path)
    assert not data_store.exists(path)



def test_delete_config_with_identifier_names_return_path(data_store):
    namespace = "software_a"
    scope_identifier = {"hostname": "w11dt000001"}
    filename = "config.yml"
    path = data_store.rootdir / Path(f"hostname/{scope_identifier['hostname']}/{namespace}/{filename}")

    result_path = delete_config(data_store=data_store, namespace=namespace,
                                filename=filename, scope_identifier=scope_identifier)
    assert result_path == str(path)
    assert not data_store.exists(path)


def test_delete_config_multi_identifiers_return_multiple_scope_identifiers_error(data_store):
    namespace = "software_a"
    scope_identifier = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = "config.yml"

    with pytest.raises(MultipleScopeIdentifiersError):
        delete_config(data_store=data_store, namespace=namespace, filename=filename,
                      scope_identifier=scope_identifier)


def test_delete_config_invalid_identifier_names_return_invalid_scope_identifier_error(data_store):
    namespace = "software_a"
    scope_identifier = {"fakefake": "value"}
    filename = "config.yml"

    with pytest.raises(InvalidScopeError):
        delete_config(data_store=data_store, namespace=namespace, filename=filename,
                      scope_identifier=scope_identifier)


@pytest.mark.parametrize(
    "namespace, scope_identifier, filename, error_type",
    [
        pytest.param(
            "new_namespace", {}, "config.yml", InvalidNamespaceError, id="missing-namespace"
            ),
        pytest.param(
            "software_a", {}, "config_new.yml", ConfigNotFoundError, id="missing-file"
            ),
        pytest.param(
            "software_a", {"hostname": "w11new"}, "config.yml", InvalidScopeIdentifierError, id="missing-scope-id"
            ),
    ],
)
def test_delete_config_missing_config_return_config_not_found_error(
    data_store, namespace, scope_identifier, filename, error_type
):
    with pytest.raises(error_type):
        delete_config(data_store=data_store, namespace=namespace, filename=filename,
            scope_identifier=scope_identifier)


def test_delete_config_path_is_directory_return_path_is_directory_error(data_store):
    """
    This in theory should not happen. API wouldn't allow for the creation of a directory like
    this. However, this could occur if users added nodes with zoonavigator.
    """
    namespace = "test_delete_path_error"
    scope_identifier = {}
    filename = "additional_node"  # this is a directory, not a file

    with pytest.raises(PathIsDirectoryError):
        delete_config(data_store=data_store, namespace=namespace, filename=filename,
                      scope_identifier=scope_identifier)
