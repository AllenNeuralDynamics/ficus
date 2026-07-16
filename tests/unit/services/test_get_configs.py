import pytest

from ficus.core.exceptions import (
    ConfigNotFoundError,
    InvalidNamespaceError,
    InvalidScopeError,
    InvalidScopeIdentifierError,
)
from ficus.schemas.configs import ConfigObject
from ficus.services.configs import (
    get_override_stack,
    get_config,
)
from pathlib import Path


################################################################################
#
#   get_config()
#
################################################################################


# @pytest.mark.parametrize("merge", [False, True])
def test_get_config_return_defaults(data_store):
    result = get_config(data_store=data_store, namespace="software_a")
    assert isinstance(result, ConfigObject)
    assert result.data == {
        "default-default-value": "the one ring",
    }
    assert result.override_stack == [data_store.rootdir / Path("defaults/software_a/default.yml")]


def test_get_config_with_identifier_name_return_config(data_store):
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001"}

    result = get_config(
        data_store=data_store, namespace=namespace, scope_identifiers=scope_identifiers,
    )

    assert isinstance(result, ConfigObject)
    assert result.data == {
        "default-default-value": "the one ring",
        "computer-default-value": "to rule them all",
    }
    assert result.override_stack == [
        data_store.rootdir / "defaults/software_a/default.yml",
        data_store.rootdir / "hostname/w11dt000001/software_a/default.json",
    ]


def test_get_config_with_identifier_names_return_config(data_store):
    namespace = "software_a"
    scope_identifiers= {"hostname": "w11dt000001", "subject_id": "614173"}

    result = get_config(
        data_store=data_store, namespace=namespace, scope_identifiers=scope_identifiers,
    )

    assert isinstance(result, ConfigObject)
    assert result.data == {
        "default-default-value": "the one ring",
        "computer-default-value": "to rule them all",
        "subject-default-value": "one config to bring them all",
    }
    assert result.override_stack == [
        data_store.rootdir / "defaults/software_a/default.yml",
        data_store.rootdir / "hostname/w11dt000001/software_a/default.json",
        data_store.rootdir / "subject_id/614173/software_a/default.json",
    ]


def test_get_config_with_mode_return_config(data_store):
    namespace = "software_a"
    scope_identifiers = {}
    mode = "config"

    result = get_config(
        data_store=data_store, namespace=namespace, scope_identifiers=scope_identifiers,
        mode=mode
    )

    assert isinstance(result, ConfigObject)
    assert result.data == {
        "default-default-value": "the one ring",
        "name": "config",
        "scope": "default",
        "default-layer-value": "beep beep",
    }
    assert result.override_stack == [
        data_store.rootdir / "defaults/software_a/default.yml",
        data_store.rootdir / "defaults/software_a/config.yml",
    ]


def test_get_config_with_mode_and_identifier_names_return_config(data_store):
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"

    result = get_config(
        data_store=data_store, namespace=namespace, scope_identifiers=scope_identifiers,
        mode=mode
    )

    assert isinstance(result, ConfigObject)
    assert result.data == {
        "default-default-value": "the one ring",
        "computer-default-value": "to rule them all",
        "subject-default-value": "one config to bring them all",
        "default-layer-value": "beep beep",
        "computer-layer-value": "boop boop",
        "subject-layer-value": "bap bap",
        "name": "config",
        "scope": "614173",
        "The Cure": "show me how you do that trick",
    }
    assert result.override_stack == [
        data_store.rootdir / "defaults/software_a/default.yml",
        data_store.rootdir / "defaults/software_a/config.yml",
        data_store.rootdir / "hostname/w11dt000001/software_a/default.json",
        data_store.rootdir / "hostname/w11dt000001/software_a/config.yml",
        data_store.rootdir / "subject_id/614173/software_a/default.json",
        data_store.rootdir / "subject_id/614173/software_a/config.yml",
    ]


# def test_get_config_no_merge_with_mode_return_config(data_store):
#     namespace = "software_a"
#     scope_identifiers = {}
#     mode = "config"
#     merge = False

#     result = get_config(
#         data_store=data_store, namespace=namespace, scope_identifiers=scope_identifiers,
#         mode=mode, merge=merge
#     )

#     assert isinstance(result, ConfigObject)
#     assert result.data == {
#         "name": "config",
#         "scope": "default",
#         "default-layer-value": "beep beep",
#     }
#     assert result.override_stack == [data_store.rootdir / "defaults/software_a/config.yml"]


# def test_get_config_no_merge_with_identifier_names_return_config(data_store):
#     namespace = "software_a"
#     scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
#     merge = False

#     result = get_config(
#         data_store=data_store, namespace=namespace, scope_identifiers=scope_identifiers,
#         merge=merge
#     )

#     assert len(result) == 2
#     assert result[0] == {
#         "subject-default-value": "one config to bring them all",
#     }
#     assert result[1] == [data_store.rootdir / "subject_id/614173/software_a/default.json"]


# def test_get_config_no_merge_with_filename_and_identifier_names_return_config(data_store):
#     namespace = "software_a"
#     scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
#     mode = "config"
#     merge = False

#     result = get_config(
#         data_store=data_store, namespace=namespace, scope_identifiers=scope_identifiers,
#         mode=mode, merge=merge
#     )

#     assert len(result) == 2
#     assert result[0] == {
#         "scope": "614173",
#         "subject-layer-value": "bap bap",
#         "The Cure": "show me how you do that trick",
#     }
#     assert result[1] == [data_store.rootdir / "subject_id/614173/software_a/config.yml"]


def test_get_config_invalid_identifiers_return_invalid_scope_error(data_store):
    with pytest.raises(InvalidScopeError):
        get_config(data_store=data_store, namespace="software_a",
                   scope_identifiers={"fake_id": "FAKE"})


def test_get_config_invalid_namespace_returns_invalid_namespace_error(data_store):
    namespace = "badbadbad"
    scope_identifiers = {}
    mode = "config"
    with pytest.raises(InvalidNamespaceError):
        get_config(
            data_store=data_store,
            namespace=namespace,
            scope_identifiers = scope_identifiers,
            mode=mode,
        )


def test_get_config_invalid_mode_returns_config_not_found_error(data_store):
    namespace = "software_a"
    scope_identifiers = {}
    mode = "config_bad"
    with pytest.raises(ConfigNotFoundError):
        get_config(
            data_store=data_store,
            namespace=namespace,
            scope_identifiers = scope_identifiers,
            mode=mode,
        )


def test_get_config_invalid_scope_identifier_raises_with_must_exist(data_store):
    namespace = "software_a"
    scope_identifiers = {"subject_id": "bad_subject_id"}
    mode = "config"
    with pytest.raises(InvalidScopeIdentifierError):
        get_config(
            data_store=data_store,
            namespace=namespace,
            scope_identifiers = scope_identifiers,
            scope_ids_must_exist={"subject_id"},
            mode=mode,
        )
        
def test_get_config_invalid_scope_identifier_is_fine(data_store):
    namespace = "software_a"
    scope_identifiers = {"subject_id": "bad_subject_id"}
    mode = "config"
    get_config(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers = scope_identifiers,
        mode=mode,
    )

def test_get_config_mode_default_return_defaults(data_store):
    """
    Ensure default file is retrieved once.
    Since default gets pulled when merging, could accidentally pull default.yml twice.
    Config content would be the same, but path should only show default.yml once.
    """
    result = get_config(data_store, "software_a", mode="default")
    assert isinstance(result, ConfigObject)
    assert result.data == {
        "default-default-value": "the one ring",
    }
    assert result.override_stack == [data_store.rootdir / "defaults/software_a/default.yml"]


#################################################################################
##
##   get_get_override_stack()
##
#################################################################################
#
#
def test_get_override_stack_with_default_mode_return_stack(data_store):
    namespace="software_a"
    scope_identifiers = {}
    mode = "default"

    result = get_override_stack(
        data_store=data_store, namespace=namespace,
        scope_identifiers=scope_identifiers, mode=mode
    )

    assert result == [
        data_store.rootdir / Path("defaults/software_a/default.yml"),
    ]

def test_get_override_stack_with_namespace_and_mode_return_stack(data_store):
    namespace="software_a"
    scope_identifiers = {}
    mode = "config"

    result = get_override_stack(
        data_store=data_store, namespace=namespace,
        scope_identifiers=scope_identifiers, mode=mode
    )

    assert result == [
        data_store.rootdir / Path("defaults/software_a/default.yml"),
        data_store.rootdir / Path("defaults/software_a/config.yml")
    ]

def test_get_override_stack_with_multi_scopes_and_mode_return_stack(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"

    result = get_override_stack(
        data_store=data_store, namespace=namespace,
        scope_identifiers=scope_identifiers, mode=mode
    )

    assert result == [
        data_store.rootdir / Path("defaults/software_a/default.yml"),
        data_store.rootdir / Path("defaults/software_a/config.yml"),
        data_store.rootdir / Path("hostname/w11dt000001/software_a/default.json"),
        data_store.rootdir / Path("hostname/w11dt000001/software_a/config.yml"),
        data_store.rootdir / Path("subject_id/614173/software_a/default.json"),
        data_store.rootdir / Path("subject_id/614173/software_a/config.yml")
    ]

#def test_get_override_stack_with_filenames_of_different_extensions_return_stack(data_store):
# TODO


# def test_get_all_files_with_identifier_names_and_filename_return_files(data_store):
#     scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}

#     result = list_all_filenames_in_lowest_scope(
#         data_store=data_store,
#         namespace="software_a",
#         scope_identifiers=scope_identifiers
#     )

#     assert result == ["config.yml", "default.json"]


#def test_get_all_files_with_identifier_names_and_partial_filename_return_files(zk_mock):
#    scope_identifiers= {"hostname": "w11dt000001", "subject_id": "614173"}
#    filename = "conf"  # partial filename, still matches
#
#    result = get_all_files(
#        namespace="software_a", scope_identifiers=scope_identifiers, filename=filename
#    )
#
#    assert len(result) == 3
#    assert result == [
#        f"{ZK_ROOT_PATH}/defaults/software_a/config.yml",
#        f"{ZK_ROOT_PATH}/hostname/w11dt000001/software_a/config.yml",
#        f"{ZK_ROOT_PATH}/subject_id/614173/software_a/config.yml",
#    ]
#
#
#def test_get_all_files_invalid_identifier_names_return_invalid_scope_error(zk_mock):
#    with pytest.raises(InvalidScopeError):
#        get_all_files(namespace="software_a", scope_identifiers={"badbad": "123"})
#
#
#@pytest.mark.parametrize(
#    "params",
#    [
#        # Bad namespace
#        {"namespace": "badbadbad", "scope_identifiers": {}},
#        # Bad identifier value
#        {"namespace": "", "scope_identifiers": {"subject_id": "badbad"}},
#    ],
#)
#def test_get_all_files_invalid_file_identifier_return_config_not_found_error(zk_mock, params):
#    with pytest.raises(ConfigNotFoundError) as err:
#        get_all_files(namespace=params["namespace"], scope_identifiers=params["scope_identifiers"])
