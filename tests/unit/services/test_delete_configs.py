import pytest


from ficus.core.exceptions import (
    ConfigNotFoundError,
    InvalidScopeIdentifierError,
    PathIsDirectoryError,
    MultipleScopeIdentifiersError,
)
from ficus.services.configs import delete_config
from tests.constants import ZK_ROOT_PATH


################################################################################
#
#   delete_config()
#
################################################################################


def test_delete_config_no_identifier_names_return_path(zk_mock):
    namespace = "software_a"
    identifier_names = {}
    filename = "config.yml"
    path = f"{ZK_ROOT_PATH}/defaults/{namespace}/{filename}"

    result_path = delete_config(namespace, filename, identifier_names)
    assert result_path == path
    assert not zk_mock.exists(path)


def test_delete_config_with_identifier_names_return_path(zk_mock):
    namespace = "software_a"
    identifier_names = {"hostname": "w11dt000001"}
    filename = "config.yml"
    path = f"{ZK_ROOT_PATH}/computers/{identifier_names['hostname']}/{namespace}/{filename}"

    result_path = delete_config(namespace, filename, identifier_names)
    assert result_path == path
    assert not zk_mock.exists(path)


def test_delete_config_multi_identifiers_return_multiple_scope_identifiers_error(zk_mock):
    namespace = "software_a"
    identifier_names = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = "config.yml"

    with pytest.raises(MultipleScopeIdentifiersError):
        delete_config(namespace, filename, identifier_names)


def test_delete_config_invalid_identifier_names_return_invalid_scope_identifier_error(zk_mock):
    namespace = "software_a"
    identifier_names = {"fakefake": "value"}
    filename = "config.yml"

    with pytest.raises(InvalidScopeIdentifierError):
        delete_config(namespace, filename, identifier_names)


@pytest.mark.parametrize(
    "namespace, identifier_names, filename",
    [
        pytest.param("new_namespace", {}, "config.yml", id="missing-namespace"),
        pytest.param("software_a", {}, "config_new.yml", id="missing-file"),
        pytest.param("software_a", {"hostname": "w11new"}, "config.yml", id="missing-scope"),
    ],
)
def test_delete_config_missing_config_return_config_not_found_error(
    zk_mock, namespace, identifier_names, filename
):
    with pytest.raises(ConfigNotFoundError):
        delete_config(namespace, filename, identifier_names)


def test_delete_config_path_is_directory_return_path_is_directory_error(zk_mock):
    """
    This in theory should not happen. API wouldn't allow for the creation of a directory like
    this. However, this could occur if users added nodes with zoonavigator.
    """
    namespace = "test_delete_path_error"
    identifier_names = {}
    filename = "additional_node"  # this is a directory, not a file

    with pytest.raises(PathIsDirectoryError):
        delete_config(namespace, filename, identifier_names)
