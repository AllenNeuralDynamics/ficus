from _pytest import scope
import pytest
from pathlib import Path

from ficus.core.exceptions import (
    ConfigNotFoundError,
    PathIsDirectoryError,
    InvalidScopeError,
    MultipleScopeIdentifiersError,
)
from ficus.services.configs import delete_config
from tests.constants import ZK_ROOT_PATH


################################################################################
#
#   delete_config()
#
################################################################################


def test_delete_config_no_identifier_names_return_path(data_store):
    namespace = "software_a"
    scope_identifiers = {}
    filename = "config.yml"
    path = data_store.rootdir / Path(f"defaults/{namespace}/{filename}")

    result_path = delete_config(data_store=data_store, namespace=namespace,
                                filename=filename, scope_identifiers=scope_identifiers)
    assert result_path == str(path)
    assert not data_store.exists(path)



def test_delete_config_with_identifier_names_return_path(data_store):
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001"}
    filename = "config.yml"
    path = data_store.rootdir / Path(f"hostname/{scope_identifiers['hostname']}/{namespace}/{filename}")

    result_path = delete_config(data_store=data_store, namespace=namespace,
                                filename=filename, scope_identifiers=scope_identifiers)
    assert result_path == str(path)
    assert not data_store.exists(path)


def test_delete_config_multi_identifiers_return_multiple_scope_identifiers_error(data_store):
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = "config.yml"

    with pytest.raises(MultipleScopeIdentifiersError):
        delete_config(data_store=data_store, namespace=namespace, filename=filename,
                      scope_identifiers=scope_identifiers)


def test_delete_config_invalid_identifier_names_return_invalid_scope_identifier_error(data_store):
    namespace = "software_a"
    scope_identifiers = {"fakefake": "value"}
    filename = "config.yml"

    with pytest.raises(InvalidScopeError):
        delete_config(data_store=data_store, namespace=namespace, filename=filename,
                      scope_identifiers=scope_identifiers)


@pytest.mark.parametrize(
    "namespace, scope_identifiers, filename",
    [
        pytest.param("new_namespace", {}, "config.yml", id="missing-namespace"),
        pytest.param("software_a", {}, "config_new.yml", id="missing-file"),
        pytest.param("software_a", {"hostname": "w11new"}, "config.yml", id="missing-scope-id"),
    ],
)
def test_delete_config_missing_config_return_config_not_found_error(
    data_store, namespace, scope_identifiers, filename
):
    with pytest.raises(ConfigNotFoundError):
        delete_config(data_store=data_store, namespace=namespace, filename=filename,
            scope_identifiers=scope_identifiers)


def test_delete_config_path_is_directory_return_path_is_directory_error(data_store):
    """
    This in theory should not happen. API wouldn't allow for the creation of a directory like
    this. However, this could occur if users added nodes with zoonavigator.
    """
    namespace = "test_delete_path_error"
    scope_identifiers = {}
    filename = "additional_node"  # this is a directory, not a file

    with pytest.raises(PathIsDirectoryError):
        delete_config(data_store=data_store, namespace=namespace, filename=filename,
                      scope_identifiers=scope_identifiers)
