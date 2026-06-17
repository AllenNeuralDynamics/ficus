import json
import pytest

from ficus.core.exceptions import (
    ConfigDecodeError,
    ConfigExistsError,
    ConfigNotFoundError,
    ConfigSerializeError,
    InvalidScopeError,
    MultipleScopeIdentifiersError,
    UnsupportedFileTypeError,
)
from ficus.services.configs import save_config, _save_config
from tests.constants import ZK_ROOT_PATH


################################################################################
#
#   save_config()
#
################################################################################


@pytest.mark.parametrize(
    "namespace, scope_identifiers, filename, override, create_if_missing",
    [
        pytest.param("new_namespace", {}, "config.yml", False, True, id="save-new-namespace"),
        pytest.param("new_namespace", {}, "default.yml", False, True, id="save-new-default-file"),
        pytest.param("software_a", {}, "config_new.yml", False, True, id="save-new-file"),
        pytest.param(
            "software", {"hostname": "w11new"}, "config.yml", False, True, id="save-new-scope"
        ),
        pytest.param("software_a", {}, "config.yml", True, True, id="override-create-if-missing"),
        pytest.param(
            "software_a", {}, "config.yml", True, False, id="override-no-create-if-missing"
        ),
    ],
)
def test_save_config_valid_return_data_and_path(
    zk_mock, namespace, scope_identifiers, filename, override, create_if_missing
):
    """
    _save_config does most of the bulk work. This unit test is just to ensure the various params
    get converted to (scope/identifier) correctly for _save_config.
    """
    if scope_identifiers == {}:
        path = f"{ZK_ROOT_PATH}/defaults/{namespace}/{filename}"
    else:
        path = f"{ZK_ROOT_PATH}/hostname/{scope_identifiers['hostname']}/{namespace}/{filename}"
    data = {"testing": "ni-haody"}

    result_data, result_path = save_config(
        namespace=namespace,
        filename=filename,
        data=data,
        scope_identifiers=scope_identifiers,
        override=override,
        create_if_missing=create_if_missing,
    )
    assert result_data == data
    assert result_path == path


def test_save_config_multiple_identifier_names_return_multiple_scopes_error(zk_mock):
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}

    with pytest.raises(MultipleScopeIdentifiersError):
        save_config(
            namespace="software_a",
            filename="config.yml",
            data={"testing": "ni-haody"},
            scope_identifiers=scope_identifiers,
        )


def test_save_config_invalid_identifier_names_return_invalid_scope_error(zk_mock):
    scope_identifiers = {"hostname-typo": "w11dt000001"}

    with pytest.raises(InvalidScopeError):
        save_config(
            namespace="software_a",
            filename="config.yml",
            data={"testing": "ni-haody"},
            scope_identifiers=scope_identifiers,
        )


def test_save_config_invalid_data_return_error(zk_mock):
    with pytest.raises(ConfigSerializeError):
        save_config(
            namespace="software_a",
            filename="config_new.yml",
            data={"testing": object()},
            scope_identifiers={},
        )


def test_save_config_invalid_file_type_return_error(zk_mock):
    with pytest.raises(UnsupportedFileTypeError):
        save_config(
            namespace="software_a",
            scope_identifiers={},
            filename="config_new.bad",
            data={},
        )


################################################################################
#
#   _save_config()
#
################################################################################


@pytest.mark.parametrize(
    "namespace, scope, identifier, filename, override, create_if_missing",
    [
        pytest.param(
            "new_namespace", None, None, "config.yml", False, True, id="save-new-namespace"
        ),
        pytest.param(
            "new_namespace", None, None, "default.yml", False, True, id="save-new-default-file"
        ),
        pytest.param(
            "software_a", None, None, "config_new_file.yml", False, True, id="save-new-file"
        ),
        pytest.param(
            "software", "hostname", "w11new", "config.yml", False, True, id="save-new-scope"
        ),
        pytest.param(
            "software_a", None, None, "config.yml", True, True, id="override-create-if-missing"
        ),
        pytest.param(
            "software_a", None, None, "config.yml", True, False, id="override-no-create-if-missing"
        ),
    ],
)
def test__save_config_valid_return_data_and_path(
    zk_mock, namespace, scope, identifier, filename, override, create_if_missing
):
    if scope and identifier:
        path = f"{ZK_ROOT_PATH}/{scope}/{identifier}/{namespace}/{filename}"
    else:
        path = f"{ZK_ROOT_PATH}/defaults/{namespace}/{filename}"

    data = {"testing": "ni-haody"}

    result_data, result_path = _save_config(
        namespace=namespace,
        scope=scope,
        identifier=identifier,
        filename=filename,
        data=json.dumps(data).encode("utf-8"),
        override=override,
        create_if_missing=create_if_missing,
    )
    assert result_data == data
    assert result_path == path


@pytest.mark.parametrize(
    "namespace, scope, identifier, filename",
    [
        pytest.param("new_namespace", None, None, "config.yml", id="namespace-missing"),
        pytest.param("software_a", "computer", "w10bad", "config.yml", id="scope-missing"),
        pytest.param("software_a", None, None, "config-bad.yml", id="filename-missing"),
    ],
)
def test__save_config_override_existing_file_return_config_not_found(
    zk_mock, namespace, scope, identifier, filename
):
    """
    ConfigNotFoundErrors only occur if user wants to override, and they don't want to create a file
    if it is missing.

    If the user gives a path to a file that they think exists, but it actually doesn't exist, then
    we want to error out since the user explicitly said to override.
    """
    override = True
    create_if_missing = False

    with pytest.raises(ConfigNotFoundError):
        _save_config(
            namespace=namespace,
            scope=scope,
            identifier=identifier,
            filename=filename,
            data={},
            override=override,
            create_if_missing=create_if_missing,
        )


@pytest.mark.parametrize(
    "filename",
    [
        pytest.param("config.yml", id="namespace-missing"),
        pytest.param("default.yml", id="namespace-missing"),
    ],
)
def test__save_config_file_exists_return_exist_error(zk_mock, filename):
    """
    Config exist errors only occur when config already exists and override is false.

    Does not matter what create-if-missing is since in this scenario the assumption is the file does
    exist and the user wants to add a file but not override anything.
    """
    namespace = "software_a"

    with pytest.raises(ConfigExistsError):
        _save_config(
            namespace=namespace,
            filename=filename,
            data={},
        )


def test__save_config_invalid_data_return_error(zk_mock):
    with pytest.raises(ConfigDecodeError):
        _save_config(
            namespace="software_a",
            filename="config_new.json",
            data=b'{"ruh: "roh-}',
        )
