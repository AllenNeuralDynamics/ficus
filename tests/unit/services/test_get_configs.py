import pytest

from ficus.core.exceptions import (
    ConfigNotFoundError,
    InvalidScopeIdentifierError,
)
from ficus.services.configs import (
    get_all_files,
    get_config,
    _get_config,
    _get_default_config,
    _get_scope_from_identifier_names,
)
from tests.constants import ZK_ROOT_NODE, ZK_ROOT_PATH


################################################################################
#
#   get_config()
#
################################################################################


@pytest.mark.parametrize("merge", [False, True])
def test_get_config_return_defaults(zk_mock, merge):
    result = get_config("software_a", merge=merge)
    assert len(result) == 2
    assert result[0] == {
        "default-default-value": "the one ring",
    }
    assert result[1] == [f"{ZK_ROOT_PATH}/defaults/software_a/default.yml"]


def test_get_config_with_identifier_name_return_config(zk_mock):
    namespace = "software_a"
    identifier_names = {"hostname": "w11dt000001"}
    filename = None
    merge = True

    result = get_config(
        namespace=namespace, identifier_names=identifier_names, filename=filename, merge=merge
    )

    assert len(result) == 2
    assert result[0] == {
        "default-default-value": "the one ring",
        "computer-default-value": "to rule them all",
    }
    assert result[1] == [
        f"{ZK_ROOT_PATH}/defaults/software_a/default.yml",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/default.json",
    ]


def test_get_config_with_identifier_names_return_config(zk_mock):
    namespace = "software_a"
    identifier_names = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = None
    merge = True

    result = get_config(
        namespace=namespace, identifier_names=identifier_names, filename=filename, merge=merge
    )

    assert len(result) == 2
    assert result[0] == {
        "default-default-value": "the one ring",
        "computer-default-value": "to rule them all",
        "subject-default-value": "one config to bring them all",
    }
    assert result[1] == [
        f"{ZK_ROOT_PATH}/defaults/software_a/default.yml",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/default.json",
        f"{ZK_ROOT_PATH}/subjects/614173/software_a/default.json",
    ]


def test_get_config_with_filename_return_config(zk_mock):
    namespace = "software_a"
    identifier_names = {}
    filename = "config.yml"
    merge = True

    result = get_config(
        namespace=namespace, identifier_names=identifier_names, filename=filename, merge=merge
    )

    assert len(result) == 2
    assert result[0] == {
        "default-default-value": "the one ring",
        "name": "config",
        "scope": "default",
        "default-layer-value": "beep beep",
    }
    assert result[1] == [
        f"{ZK_ROOT_PATH}/defaults/software_a/default.yml",
        f"{ZK_ROOT_PATH}/defaults/software_a/config.yml",
    ]


def test_get_config_with_filename_and_identifier_names_return_config(zk_mock):
    namespace = "software_a"
    identifier_names = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = "config.yml"
    merge = True

    result = get_config(
        namespace=namespace, identifier_names=identifier_names, filename=filename, merge=merge
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
        f"{ZK_ROOT_PATH}/defaults/software_a/default.yml",
        f"{ZK_ROOT_PATH}/defaults/software_a/config.yml",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/default.json",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/config.yml",
        f"{ZK_ROOT_PATH}/subjects/614173/software_a/default.json",
        f"{ZK_ROOT_PATH}/subjects/614173/software_a/config.yml",
    ]


def test_get_config_no_merge_with_filename_return_config(zk_mock):
    namespace = "software_a"
    identifier_names = {}
    filename = "config.yml"
    merge = False

    result = get_config(
        namespace=namespace, identifier_names=identifier_names, filename=filename, merge=merge
    )

    assert len(result) == 2
    assert result[0] == {
        "name": "config",
        "scope": "default",
        "default-layer-value": "beep beep",
    }
    assert result[1] == [f"{ZK_ROOT_PATH}/defaults/software_a/config.yml"]


def test_get_config_no_merge_with_identifier_names_return_config(zk_mock):
    namespace = "software_a"
    identifier_names = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = None
    merge = False

    result = get_config(
        namespace=namespace, identifier_names=identifier_names, filename=filename, merge=merge
    )

    assert len(result) == 2
    assert result[0] == {
        "subject-default-value": "one config to bring them all",
    }
    assert result[1] == [f"{ZK_ROOT_PATH}/subjects/614173/software_a/default.json"]


def test_get_config_no_merge_with_filename_and_identifier_names_return_config(zk_mock):
    namespace = "software_a"
    identifier_names = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = "config.yml"
    merge = False

    result = get_config(
        namespace=namespace, identifier_names=identifier_names, filename=filename, merge=merge
    )

    assert len(result) == 2
    assert result[0] == {
        "scope": "614173",
        "subject-layer-value": "bap bap",
        "The Cure": "show me how you do that trick",
    }
    assert result[1] == [f"{ZK_ROOT_PATH}/subjects/614173/software_a/config.yml"]


def test_get_config_invalid_identifiers_return_invalid_scope_error(zk_mock):
    with pytest.raises(InvalidScopeIdentifierError) as err:
        get_config("software_a", identifier_names={"fake_id": "FAKE"})
    assert "Invalid scope identifier name" in str(err.value)


@pytest.mark.parametrize(
    "params",
    [
        # Bad namespace
        {"namespace": "badbadbad", "identifier_names": {}, "filename": "config.yml"},
        # Bad filename
        {"namespace": "software_a", "identifier_names": {}, "filename": "config.bad"},
        # Bad identifier value
        {
            "namespace": "software_a",
            "identifier_names": {"subject_id": "bad_subject_id"},
            "filename": "config.yml",
        },
    ],
)
def test_get_config_invalid_namespace_filename_returns_config_not_found_error(zk_mock, params):
    with pytest.raises(ConfigNotFoundError):
        get_config(
            namespace=params["namespace"],
            identifier_names=params["identifier_names"],
            filename=params["filename"],
        )


def test_get_config_filename_default_return_defaults(zk_mock):
    """
    Ensure default file is retrieved once.
    Since default gets pulled when merging, could accidentally pull default.yml twice.
    Config content would be the same, but path should only show default.yml once.
    """
    result = get_config("software_a", filename="default.yml")
    assert len(result) == 2
    assert result[0] == {
        "default-default-value": "the one ring",
    }
    assert result[1] == [f"{ZK_ROOT_PATH}/defaults/software_a/default.yml"]


################################################################################
#
#   get_all_files()
#
################################################################################


def test_get_all_files_return_files(zk_mock):
    result = get_all_files(namespace="software_a")

    assert len(result) == 2
    assert result == [
        f"{ZK_ROOT_PATH}/defaults/software_a/default.yml",
        f"{ZK_ROOT_PATH}/defaults/software_a/config.yml",
    ]


def test_get_all_files_with_identifier_names_return_default_files(zk_mock):
    identifier_names = {"hostname": "w11dt000001"}
    filename = None

    result = get_all_files(
        namespace="software_a", identifier_names=identifier_names, filename=filename
    )

    assert len(result) == 4
    assert result == [
        f"{ZK_ROOT_PATH}/defaults/software_a/default.yml",
        f"{ZK_ROOT_PATH}/defaults/software_a/config.yml",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/default.json",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/config.yml",
    ]


def test_get_all_files_with_multi_identifier_names_return_default_files(zk_mock):
    identifier_names = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = None

    result = get_all_files(
        namespace="software_a", identifier_names=identifier_names, filename=filename
    )

    assert len(result) == 6
    assert result == [
        f"{ZK_ROOT_PATH}/defaults/software_a/default.yml",
        f"{ZK_ROOT_PATH}/defaults/software_a/config.yml",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/default.json",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/config.yml",
        f"{ZK_ROOT_PATH}/subjects/614173/software_a/default.json",
        f"{ZK_ROOT_PATH}/subjects/614173/software_a/config.yml",
    ]


def test_get_all_files_with_filename_return_files(zk_mock):
    identifier_names = {}
    filename = "config.yml"

    result = get_all_files(
        namespace="software_a", identifier_names=identifier_names, filename=filename
    )

    assert len(result) == 1
    assert result == [
        f"{ZK_ROOT_PATH}/defaults/software_a/config.yml",
    ]


def test_get_all_files_with_identifier_names_and_filename_return_files(zk_mock):
    identifier_names = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = "config.yml"

    result = get_all_files(
        namespace="software_a", identifier_names=identifier_names, filename=filename
    )

    assert len(result) == 3
    assert result == [
        f"{ZK_ROOT_PATH}/defaults/software_a/config.yml",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/config.yml",
        f"{ZK_ROOT_PATH}/subjects/614173/software_a/config.yml",
    ]


def test_get_all_files_with_identifier_names_and_partial_filename_return_files(zk_mock):
    identifier_names = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = "conf"  # partial filename, still matches

    result = get_all_files(
        namespace="software_a", identifier_names=identifier_names, filename=filename
    )

    assert len(result) == 3
    assert result == [
        f"{ZK_ROOT_PATH}/defaults/software_a/config.yml",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/config.yml",
        f"{ZK_ROOT_PATH}/subjects/614173/software_a/config.yml",
    ]


def test_get_all_files_invalid_identifier_names_return_invalid_scope_error(zk_mock):
    with pytest.raises(InvalidScopeIdentifierError) as err:
        get_all_files(namespace="software_a", identifier_names={"badbad": "123"})
    assert "Invalid scope identifier name" in str(err.value)


@pytest.mark.parametrize(
    "params",
    [
        # Bad namespace
        {"namespace": "badbadbad", "identifier_names": {}},
        # Bad identifier value
        {"namespace": "", "identifier_names": {"subject_id": "badbad"}},
    ],
)
def test_get_all_files_invalid_file_identifier_return_config_not_found_error(zk_mock, params):
    with pytest.raises(ConfigNotFoundError) as err:
        get_all_files(namespace=params["namespace"], identifier_names=params["identifier_names"])
    assert "not found" in str(err.value)


################################################################################
#
#   _get_config() and _get_default_config()
#
################################################################################


def test__get_config_return_config(zk_mock):
    result = _get_config(zk_mock, f"{ZK_ROOT_PATH}/defaults/software_a/config.yml")
    assert result == {
        "name": "config",
        "scope": "default",
        "default-layer-value": "beep beep",
    }


def test__get_config_invalid_subpath_return_config_not_found_error(zk_mock):
    with pytest.raises(ConfigNotFoundError) as err:
        _get_config(zk_mock, f"{ZK_ROOT_NODE}/defaults/BAD_SUBPATH/config.yml")
    assert f"Subpath '{ZK_ROOT_NODE}/defaults/BAD_SUBPATH' not found" in str(err.value)


def test__get_config_invalid_filename_return_config_not_found_error(zk_mock):
    with pytest.raises(ConfigNotFoundError) as err:
        _get_config(zk_mock, f"{ZK_ROOT_NODE}/defaults/software_a/config_FAKE.yml")
    assert "Config file not found" in str(err.value)


def test__get_config_no_filename_return_config_not_found_error(zk_mock):
    with pytest.raises(ConfigNotFoundError) as err:
        _get_config(zk_mock, f"{ZK_ROOT_NODE}/defaults/BAD_SUBPATH")
    assert "Config file not found" in str(err.value)


def test__get_default_config_return_config(zk_mock):
    result = _get_default_config(zk_mock, f"{ZK_ROOT_PATH}/defaults/software_a")
    assert result[0] == {"default-default-value": "the one ring"}
    assert result[1] == f"{ZK_ROOT_PATH}/defaults/software_a/default.yml"


def test__get_default_config_invalid_path_return_config_not_found_error(zk_mock):
    with pytest.raises(ConfigNotFoundError) as err:
        _get_default_config(zk_mock, f"{ZK_ROOT_PATH}/defaults/software_a/badbadpath")
    assert "Default file not found" in str(err.value)


def test__get_default_config_invalid_filename_return_config_not_found_error(zk_mock):
    with pytest.raises(ConfigNotFoundError) as err:
        _get_default_config(zk_mock, f"{ZK_ROOT_PATH}/defaults/software_a/default.yml")
    assert "Default file not found" in str(err.value)


################################################################################
#
#   _get_scope_from_identifier_names()
#
################################################################################


def test__get_scope_from_identifier_names_return_scopes(zk_mock):
    identifier_names = {"hostname": "w11dt000001", "subject_id": "614173"}
    result = _get_scope_from_identifier_names(identifier_names)
    assert result == {
        "computers": "w11dt000001",
        "subjects": "614173",
    }


def test__get_scope_from_identifier_names_invalid_identifier_name_return_invalid_scope(zk_mock):
    with pytest.raises(InvalidScopeIdentifierError) as err:
        _get_scope_from_identifier_names({"badbad": "123"})
    assert "Invalid scope identifier name" in str(err.value)
