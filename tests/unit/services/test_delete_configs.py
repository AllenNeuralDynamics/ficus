import pytest
from pathlib import Path

from ficus.core.exceptions import (
    ConfigNotFoundError,
    InvalidScopeIdentifierError,
    InvalidNamespaceError,
    InvalidScopeError,
    MultipleScopeIdentifiersError,
)
from ficus.services.configs import delete_config, _delete_one_config_override


################################################################################
#
#   _delete_one_config_override()
#
################################################################################


def test_delete_one_config_override_no_identifier_names_return_path(data_store):
    namespace = "software_a"
    scope_identifier = {}
    mode = "config"
    path = data_store.rootdir / Path(f"defaults/{namespace}/{mode}.yml")

    result_path = _delete_one_config_override(data_store=data_store, namespace=namespace,
                                mode=mode, scope_identifier=scope_identifier)
    assert result_path == str(path)
    assert not data_store.exists(path)



def test_delete_one_config_override_with_identifier_names_return_path(data_store):
    namespace = "software_a"
    scope_identifier = {"hostname": "w11dt000001"}
    mode = "config"
    path = data_store.rootdir / Path(f"hostname/{scope_identifier['hostname']}/{namespace}/{mode}.yml")

    result_path = _delete_one_config_override(data_store=data_store, namespace=namespace,
                                mode=mode, scope_identifier=scope_identifier)
    assert result_path == str(path)
    assert not data_store.exists(path)


def test_delete_one_config_override_multi_identifiers_return_multiple_scope_identifiers_error(data_store):
    namespace = "software_a"
    scope_identifier = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"

    with pytest.raises(MultipleScopeIdentifiersError):
        _delete_one_config_override(data_store=data_store, namespace=namespace, mode=mode,
                      scope_identifier=scope_identifier)


def test_delete_one_config_override_invalid_identifier_names_return_invalid_scope_identifier_error(data_store):
    namespace = "software_a"
    scope_identifier = {"fakefake": "value"}
    mode = "config"

    with pytest.raises(InvalidScopeError):
        _delete_one_config_override(data_store=data_store, namespace=namespace, mode=mode,
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
def test_delete_one_config_override_missing_config_return_config_not_found_error(
    data_store, namespace, scope_identifier, mode, error_type
):
    with pytest.raises(error_type):
        _delete_one_config_override(data_store=data_store, namespace=namespace, mode=mode,
            scope_identifier=scope_identifier)


def test_delete_one_config_override_path_is_directory_return_error(data_store):
    """
    This in theory should not happen. API wouldn't allow for the creation of a directory like
    this. However, this could occur if users added nodes with zoonavigator.
    """
    namespace = "test_delete_path_error"
    scope_identifier = {}

    data_store.create(data_store.rootdir / Path(f"defaults/{namespace}/additional_node"), data=None)
    mode = "additional_node"  # this is a directory, not a file

    with pytest.raises(ConfigNotFoundError):
        _delete_one_config_override(data_store=data_store, namespace=namespace, mode=mode,
                      scope_identifier=scope_identifier)


################################################################################
#
#   delete_config_deep()
#
################################################################################


def _software_a_config_paths(data_store):
    return [
        data_store.rootdir / Path("defaults/software_a/config.yml"),
        data_store.rootdir / Path("hostname/w11dt000001/software_a/config.yml"),
        data_store.rootdir / Path("subject_id/614173/software_a/config.yml"),
    ]


def _software_a_default_paths(data_store):
    return [
        data_store.rootdir / Path("defaults/software_a/default.yml"),
        data_store.rootdir / Path("hostname/w11dt000001/software_a/default.json"),
        data_store.rootdir / Path("subject_id/614173/software_a/default.json"),
    ]


def test_delete_config_removes_mode_across_all_scopes(data_store):
    """The mode config is deleted in every scope while default configs remain."""
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    config_paths = _software_a_config_paths(data_store)
    default_paths = _software_a_default_paths(data_store)

    delete_config(data_store=data_store, namespace=namespace,
                       scope_identifiers=scope_identifiers, mode="config")

    for path in config_paths:
        assert not data_store.exists(path)
    for path in default_paths:
        assert data_store.exists(path)


def test_delete_config_delete_defaults_removes_all(data_store):
    """With delete_defaults=True both mode and default configs are removed."""
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    all_paths = _software_a_config_paths(data_store) + _software_a_default_paths(data_store)

    delete_config(data_store=data_store, namespace=namespace,
                       scope_identifiers=scope_identifiers, mode="config",
                       delete_defaults=True)

    for path in all_paths:
        assert not data_store.exists(path)


def test_delete_config_default_scope_only(data_store):
    """With no scope identifiers only the default scope mode config is removed."""
    namespace = "software_a"
    config_path = data_store.rootdir / Path("defaults/software_a/config.yml")
    default_path = data_store.rootdir / Path("defaults/software_a/default.yml")

    delete_config(data_store=data_store, namespace=namespace,
                       scope_identifiers={}, mode="config")

    assert not data_store.exists(config_path)
    assert data_store.exists(default_path)


def test_delete_config_missing_mode_raises(data_store):
    """A mode absent from the override stack raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        delete_config(data_store=data_store, namespace="software_a",
                           scope_identifiers={"hostname": "w11dt000001"},
                           mode="config_new")
