import pytest

from ficus.core.exceptions import (
    ConfigNotFoundError,
    InvalidScopeError,
    InvalidScopeIdentifierError,
)
from ficus.services.configs import (
    list_all_filenames,
    get_all_override_stacks,
    get_file_override_stack,
    get_config,
    _get_config,
    _get_default_config,
)
from tests.constants import ZK_ROOT_NODE, ZK_ROOT_PATH
from pathlib import Path


################################################################################
#
#   get_config()
#
################################################################################


@pytest.mark.parametrize("merge", [False, True])
def test_get_config_return_defaults(data_store, merge):
    result = get_config(data_store=data_store, namespace="software_a", merge=merge)
    assert len(result) == 2
    assert result[0] == {
        "default-default-value": "the one ring",
    }
    assert result[1] == [data_store.rootdir / Path("defaults/software_a/default.yml")]


def test_get_config_with_identifier_name_return_config(data_store):
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001"}
    filename = None
    merge = True

    result = get_config(
        data_store=data_store, namespace=namespace, scope_identifiers=scope_identifiers,
        filename=filename, merge=merge
    )

    assert len(result) == 2
    assert result[0] == {
        "default-default-value": "the one ring",
        "computer-default-value": "to rule them all",
    }
    assert result[1] == [
        data_store.rootdir / "defaults/software_a/default.yml",
        data_store.rootdir / "hostname/w11dt000001/software_a/default.json",
    ]


def test_get_config_with_identifier_names_return_config(data_store):
    namespace = "software_a"
    scope_identifiers= {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = None
    merge = True

    result = get_config(
        data_store=data_store, namespace=namespace, scope_identifiers=scope_identifiers,
        filename=filename, merge=merge
    )

    assert len(result) == 2
    assert result[0] == {
        "default-default-value": "the one ring",
        "computer-default-value": "to rule them all",
        "subject-default-value": "one config to bring them all",
    }
    assert result[1] == [
        data_store.rootdir / "defaults/software_a/default.yml",
        data_store.rootdir / "hostname/w11dt000001/software_a/default.json",
        data_store.rootdir / "subject_id/614173/software_a/default.json",
    ]


def test_get_config_with_filename_return_config(data_store):
    namespace = "software_a"
    scope_identifiers = {}
    filename = "config.yml"
    merge = True

    result = get_config(
        data_store=data_store, namespace=namespace, scope_identifiers=scope_identifiers,
        filename=filename, merge=merge
    )

    assert len(result) == 2
    assert result[0] == {
        "default-default-value": "the one ring",
        "name": "config",
        "scope": "default",
        "default-layer-value": "beep beep",
    }
    assert result[1] == [
        data_store.rootdir / "defaults/software_a/default.yml",
        data_store.rootdir / "defaults/software_a/config.yml",
    ]


def test_get_config_with_filename_and_identifier_names_return_config(data_store):
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = "config.yml"
    merge = True

    result = get_config(
        data_store=data_store, namespace=namespace, scope_identifiers=scope_identifiers,
        filename=filename, merge=merge
    )

    assert len(result) == 2
    assert result[0] == {
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
    assert result[1] == [
        data_store.rootdir / "defaults/software_a/default.yml",
        data_store.rootdir / "defaults/software_a/config.yml",
        data_store.rootdir / "hostname/w11dt000001/software_a/default.json",
        data_store.rootdir / "hostname/w11dt000001/software_a/config.yml",
        data_store.rootdir / "subject_id/614173/software_a/default.json",
        data_store.rootdir / "subject_id/614173/software_a/config.yml",
    ]


def test_get_config_no_merge_with_filename_return_config(data_store):
    namespace = "software_a"
    scope_identifiers = {}
    filename = "config.yml"
    merge = False

    result = get_config(
        data_store=data_store, namespace=namespace, scope_identifiers=scope_identifiers,
        filename=filename, merge=merge
    )

    assert len(result) == 2
    assert result[0] == {
        "name": "config",
        "scope": "default",
        "default-layer-value": "beep beep",
    }
    assert result[1] == [data_store.rootdir / "defaults/software_a/config.yml"]


def test_get_config_no_merge_with_identifier_names_return_config(data_store):
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = None
    merge = False

    result = get_config(
        data_store=data_store, namespace=namespace, scope_identifiers=scope_identifiers,
        filename=filename, merge=merge
    )

    assert len(result) == 2
    assert result[0] == {
        "subject-default-value": "one config to bring them all",
    }
    assert result[1] == [data_store.rootdir / "subject_id/614173/software_a/default.json"]


def test_get_config_no_merge_with_filename_and_identifier_names_return_config(data_store):
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = "config.yml"
    merge = False

    result = get_config(
        data_store=data_store, namespace=namespace, scope_identifiers=scope_identifiers,
        filename=filename, merge=merge
    )

    assert len(result) == 2
    assert result[0] == {
        "scope": "614173",
        "subject-layer-value": "bap bap",
        "The Cure": "show me how you do that trick",
    }
    assert result[1] == [data_store.rootdir / "subject_id/614173/software_a/config.yml"]


def test_get_config_invalid_identifiers_return_invalid_scope_error(data_store):
    with pytest.raises(InvalidScopeError):
        get_config(data_store=data_store, namespace="software_a",
                   scope_identifiers={"fake_id": "FAKE"})


# FIXME: should these be returning more specific kinds of errors?
# InvalidScopeIdentifierError, InvalidScopeError, etc?
@pytest.mark.parametrize(
    "params",
    [
        # Bad namespace
        {"namespace": "badbadbad", "scope_identifiers": {}, "filename": "config.yml"},
        # Bad filename
        {"namespace": "software_a", "scope_identifiers": {}, "filename": "config.bad"},
        # Bad identifier value
        {
            "namespace": "software_a",
            "scope_identifiers": {"subject_id": "bad_subject_id"},
            "filename": "config.yml",
        },
    ],
)
def test_get_config_invalid_namespace_filename_returns_config_not_found_error(data_store, params):
    with pytest.raises(ConfigNotFoundError):
        get_config(
            data_store=data_store,
            namespace=params["namespace"],
            scope_identifiers = params["scope_identifiers"],
            filename=params["filename"],
        )


def test_get_config_filename_default_return_defaults(data_store):
    """
    Ensure default file is retrieved once.
    Since default gets pulled when merging, could accidentally pull default.yml twice.
    Config content would be the same, but path should only show default.yml once.
    """
    result = get_config(data_store, "software_a", filename="default.yml")
    assert len(result) == 2
    assert result[0] == {
        "default-default-value": "the one ring",
    }
    assert result[1] == [data_store.rootdir / "defaults/software_a/default.yml"]


#################################################################################
##
##   get_get_file_override_stack()
##
#################################################################################
#
#
def test_get_override_stack_with_default_filename_return_stack(data_store):
    namespace="software_a"
    scope_identifiers = {}
    filename = "default.yml"

    result = get_file_override_stack(
        data_store=data_store, namespace=namespace,
        scope_identifiers=scope_identifiers, filename=filename
    )

    assert result == [
        data_store.rootdir / Path("defaults/software_a/default.yml"),
    ]

def test_get_override_stack_with_namespace_and_filename_return_stack(data_store):
    namespace="software_a"
    scope_identifiers = {}
    filename = "config.yml"

    result = get_file_override_stack(
        data_store=data_store, namespace=namespace,
        scope_identifiers=scope_identifiers, filename=filename
    )

    assert result == [
        data_store.rootdir / Path("defaults/software_a/default.yml"),
        data_store.rootdir / Path("defaults/software_a/config.yml")
    ]

def test_get_override_stack_with_multi_scopes_and_filename_return_stack(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = "config.yml"

    result = get_file_override_stack(
        data_store=data_store, namespace=namespace,
        scope_identifiers=scope_identifiers, filename=filename
    )

    assert result == [
        data_store.rootdir / Path("defaults/software_a/default.yml"),
        data_store.rootdir / Path("defaults/software_a/config.yml"),
        data_store.rootdir / Path("hostname/w11dt000001/software_a/default.json"),
        data_store.rootdir / Path("hostname/w11dt000001/software_a/config.yml"),
        data_store.rootdir / Path("subject_id/614173/software_a/default.json"),
        data_store.rootdir / Path("subject_id/614173/software_a/config.yml")
    ]


#################################################################################
##
##   get_all_override_stacks()
##
#################################################################################
#
#
def test_get_all_override_stacks_default_scope_return_override_stacks(data_store):
    result = get_all_override_stacks(data_store=data_store, namespace="software_a")

    assert len(result) == 2
    assert result == [
        [
            data_store.rootdir / Path("defaults/software_a/default.yml"),
            data_store.rootdir / Path("defaults/software_a/config.yml"),
        ],
        [
            data_store.rootdir / Path("defaults/software_a/default.yml"),
        ]
    ]


def test_get_all_override_stacks_with_hostname_return_override_stacks(data_store):
    scope_identifiers = {"hostname": "w11dt000001"}

    result = get_all_override_stacks(
        data_store=data_store, namespace="software_a",
        scope_identifiers=scope_identifiers)

    assert len(result) == 2
    assert result == [
        [
            data_store.rootdir / Path("defaults/software_a/default.yml"),
            data_store.rootdir / Path("defaults/software_a/config.yml"),
            data_store.rootdir / Path("hostname/w11dt000001/software_a/default.json"),
            data_store.rootdir / Path("hostname/w11dt000001/software_a/config.yml"),
        ],
        [
            data_store.rootdir / Path("defaults/software_a/default.yml"),
            data_store.rootdir / Path("hostname/w11dt000001/software_a/default.json"),
        ]
    ]


def test_get_all_override_stacks_with_multi_identifier_names_return_override_stacks(data_store):
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}

    result = get_all_override_stacks(
        data_store=data_store,
        namespace="software_a",
        scope_identifiers=scope_identifiers)

    assert len(result) == 2
    assert result == [
        [
            data_store.rootdir / Path("defaults/software_a/default.yml"),
            data_store.rootdir / Path("defaults/software_a/config.yml"),
            data_store.rootdir / Path("hostname/w11dt000001/software_a/default.json"),
            data_store.rootdir / Path("hostname/w11dt000001/software_a/config.yml"),
            data_store.rootdir / Path("subject_id/614173/software_a/default.json"),
            data_store.rootdir / Path("subject_id/614173/software_a/config.yml")
        ],
        [
            data_store.rootdir / Path("defaults/software_a/default.yml"),
            data_store.rootdir / Path("hostname/w11dt000001/software_a/default.json"),
            data_store.rootdir / Path("subject_id/614173/software_a/default.json")
        ],
    ]



#def test_get_all_files_with_identifier_names_and_filename_return_files(zk_mock):
#    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
#    filename = "config.yml"
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
#
#
#################################################################################
##
##   _get_config() and _get_default_config()
##
#################################################################################
#
#
#def test__get_config_return_config(zk_mock):
#    result = _get_config(zk_mock, f"{ZK_ROOT_PATH}/defaults/software_a/config.yml")
#    assert result == {
#        "name": "config",
#        "scope": "default",
#        "default-layer-value": "beep beep",
#    }
#
#
#def test__get_config_invalid_subpath_return_config_not_found_error(zk_mock):
#    with pytest.raises(ConfigNotFoundError) as err:
#        _get_config(zk_mock, f"{ZK_ROOT_NODE}/defaults/BAD_SUBPATH/config.yml")
#    assert f"Subpath '{ZK_ROOT_NODE}/defaults/BAD_SUBPATH' not found" in str(err.value)
#
#
#def test__get_config_invalid_filename_return_config_not_found_error(zk_mock):
#    with pytest.raises(ConfigNotFoundError) as err:
#        _get_config(zk_mock, f"{ZK_ROOT_NODE}/defaults/software_a/config_FAKE.yml")
#    assert "Config file not found" in str(err.value)
#
#
#def test__get_config_no_filename_return_config_not_found_error(zk_mock):
#    with pytest.raises(ConfigNotFoundError) as err:
#        _get_config(zk_mock, f"{ZK_ROOT_NODE}/defaults/BAD_SUBPATH")
#    assert "Config file not found" in str(err.value)
#
#
#def test__get_default_config_return_config(zk_mock):
#    result = _get_default_config(zk_mock, f"{ZK_ROOT_PATH}/defaults/software_a")
#    assert result[0] == {"default-default-value": "the one ring"}
#    assert result[1] == f"{ZK_ROOT_PATH}/defaults/software_a/default.yml"
#
#
#def test__get_default_config_invalid_path_return_config_not_found_error(zk_mock):
#    with pytest.raises(ConfigNotFoundError) as err:
#        _get_default_config(zk_mock, f"{ZK_ROOT_PATH}/defaults/software_a/badbadpath")
#    assert "Default file not found" in str(err.value)
#
#
#def test__get_default_config_invalid_filename_return_config_not_found_error(zk_mock):
#    with pytest.raises(ConfigNotFoundError) as err:
#        _get_default_config(zk_mock, f"{ZK_ROOT_PATH}/defaults/software_a/default.yml")
#    assert "Default file not found" in str(err.value)
#
