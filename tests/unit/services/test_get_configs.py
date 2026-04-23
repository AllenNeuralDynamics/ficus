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


################################################################################
#
#   get_all_files()
#
################################################################################


def test_get_all_files(zk_mock):
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
#
#
################################################################################


def test_no_filename_no_hostname(zk_mock):
    """Grab configs with following behavior:
    - no filename given
    - no hostname given
    """
    result = get_config("software_a")
    assert len(result) == 2
    assert result[0] == {
        "default-default-value": "the one ring",
    }
    assert result[1] == [f"{ZK_ROOT_PATH}/defaults/software_a/default.yml"]


def test_no_filename(zk_mock):
    """Grab configs with following behavior:
    - no filename given
    """
    result = get_config(namespace="software_a", hostname="w11dt000001")
    assert len(result) == 2
    assert result[0] == {
        "default-default-value": "the one ring",
        "computer-default-value": "to rule them all",
    }
    expected_paths = [
        f"{ZK_ROOT_PATH}/defaults/software_a/default.yml",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/default.json",
    ]
    expected_paths.sort()
    result[1].sort()
    assert result[1] == expected_paths


def test_get_config_defaults_default_file(zk_mock):
    """Grab configs with following behavior:
    - merges files (should combine default.yml and <filename>)
    - grab from /defaults directory
    """
    result = get_config("software_a", "config.yml")
    assert len(result) == 2
    assert result[0] == {
        "default-default-value": "the one ring",
        "name": "config",
        "scope": "default",
        "default-layer-value": "beep beep",
    }
    expected = [
        f"{ZK_ROOT_PATH}/defaults/software_a/default.yml",
        f"{ZK_ROOT_PATH}/defaults/software_a/config.yml",
    ]
    assert sorted(result[1]) == sorted(expected)


def test_get_config_only_computers(zk_mock):
    """Grab configs with following behavior:
    - <filename> doesn't exist in /defaults path
    - <filename> exists in /computers/<hostname> path
    """
    with pytest.raises(ConfigNotFoundError):
        get_config("software_b", "config.yml", "w11dt000001")


def test_get_merge_all(zk_mock):
    """Grabs config merging all relevant files (hostname overrides & default files)"""
    result = get_config("software_a", "config.yml", "w11dt000001")
    assert len(result) == 2
    print(result[0])
    assert result[0] == {
        "default-default-value": "the one ring",  # append from defaults/.../default.yml
        "computer-default-value": "to rule them all",  # append from computers/.../default.json
        "name": "config",  # keep from defaults/.../config.yml
        "default-layer-value": "beep beep",  # keep from defaults/.../config.yml
        "computer-layer-value": "boop boop",  # append from computers/.../config.yml
        "scope": "w11dt000001",  # overridden by computers/.../config.yml
    }
    expected = [
        f"{ZK_ROOT_PATH}/defaults/software_a/default.yml",
        f"{ZK_ROOT_PATH}/defaults/software_a/config.yml",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/default.json",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/config.yml",
    ]
    assert sorted(result[1]) == sorted(expected)


def test_invalid_namespace_defaults(zk_mock):
    """Test namespace that doesn't exist in defaults"""
    with pytest.raises(ConfigNotFoundError):
        get_config("software_FAKE", "config.yml")


def test_invalid_filename_defaults(zk_mock):
    """Test namespace that doesn't exist in defaults"""
    with pytest.raises(ConfigNotFoundError):
        get_config("software_a", "config_FAKE.yml")


def test_invalid_namespace_hostname(zk_mock):
    """Test namespace/filename that exists in default but not computers/hostname"""
    with pytest.raises(ConfigNotFoundError):
        get_config("software_a_default_only", "config.yml", "w11dt000001")


def test_invalid_hostname(zk_mock):
    """Test namespace/filename that exists but hostname doesn't"""
    with pytest.raises(ConfigNotFoundError):
        get_config("software_a", "config.yml", "w11dt000001typo")


def test_get_all_files_no_hostname(zk_mock):
    namespace = "software_a"
    files = [
        f"{ZK_ROOT_PATH}/defaults/software_a/default.yml",
        f"{ZK_ROOT_PATH}/defaults/software_a/config.yml",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/default.json",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/config.yml",
        f"{ZK_ROOT_PATH}/computers/w11dt000002/software_a/default.yaml",
        f"{ZK_ROOT_PATH}/computers/w11dt000002/software_a/config2.yml",
        f"{ZK_ROOT_PATH}/computers/w11dt000002/software_a/config3.json",
    ]
    results = get_all_files(namespace)
    assert sorted(files) == sorted(results)


def test_get_all_files_specific_hostname(zk_mock):
    namespace = "software_a"
    hostname = "w11dt000001"
    files = [
        f"{ZK_ROOT_PATH}/defaults/software_a/default.yml",
        f"{ZK_ROOT_PATH}/defaults/software_a/config.yml",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/default.json",
        f"{ZK_ROOT_PATH}/computers/w11dt000001/software_a/config.yml",
    ]
    results = get_all_files(namespace, hostname)
    assert sorted(files) == sorted(results)


def test_get_all_files_invalid_namespace(zk_mock):
    namespace = "software_a_fake"
    assert [] == get_all_files(namespace)


def test_get_all_files_invalid_hostname(zk_mock):
    namespace = "software_a"
    hostname = "w11dt000001typo"
    files = [
        f"{ZK_ROOT_PATH}/defaults/software_a/default.yml",
        f"{ZK_ROOT_PATH}/defaults/software_a/config.yml",
    ]
    assert files == get_all_files(namespace, hostname)


def test__get_config(zk_mock):
    result = _get_config(zk_mock, f"{ZK_ROOT_PATH}/defaults/software_a/config.yml")
    assert result == {
        "name": "config",
        "scope": "default",
        "default-layer-value": "beep beep",
    }


def test__get_config_invalid_subpath(zk_mock):
    """Test _get_config with invalid subpath, error message should indicate which subpath is invalid"""
    with pytest.raises(ConfigNotFoundError) as err:
        _get_config(zk_mock, f"{ZK_ROOT_NODE}/defaults/BAD_SUBPATH/config.yml")
    assert (
        f"Subpath '{ZK_ROOT_NODE}/defaults/BAD_SUBPATH' not found in path: {ZK_ROOT_NODE}/defaults/BAD_SUBPATH/config.yml"
        in str(err.value)
    )


def test__get_config_invalid_filename(zk_mock):
    """Test _get_config with invalid filename, error message should indicate config file not found at path"""
    with pytest.raises(ConfigNotFoundError) as err:
        _get_config(zk_mock, f"{ZK_ROOT_NODE}/defaults/software_a/config_FAKE.yml")
    print(str(err.value))
    assert (
        f"Config file not found at path: {ZK_ROOT_NODE}/defaults/software_a/config_FAKE.yml"
        in str(err.value)
    )


def test__get_default_config(zk_mock):
    result = _get_default_config(zk_mock, f"{ZK_ROOT_PATH}/defaults/software_a")
    assert result[0] == {"default-default-value": "the one ring"}
    assert result[1] == f"{ZK_ROOT_PATH}/defaults/software_a/default.yml"


def test__get_default_config_invalid_path(zk_mock):
    with pytest.raises(ConfigNotFoundError) as err:
        _get_default_config(zk_mock, f"{ZK_ROOT_PATH}/defaults/software_a/badbadpath")
    print(str(err.value))
    assert (
        f"Default file not found at path: {ZK_ROOT_PATH}/defaults/software_a/badbadpath/default.[yml/yaml/json]"
        in str(err.value)
    )
