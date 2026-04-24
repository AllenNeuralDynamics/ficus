import pytest

from ficus.core.exceptions import (
    ConfigNotFoundError,
    ConfigExistsError,
    ConfigSerializeError,
    InvalidScopeIdentifierError,
    MultipleScopeIdentifiersError,
)
from ficus.services.configs import save_config, _save_config
from tests.constants import ZK_ROOT_PATH


################################################################################
#
#   save_config
#
################################################################################


@pytest.mark.parametrize(
    "namespace, identifier_names, filename, override, create_if_missing",
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
    zk_mock, namespace, identifier_names, filename, override, create_if_missing
):
    if identifier_names == {}:
        path = f"{ZK_ROOT_PATH}/defaults/{namespace}/{filename}"
    else:
        path = f"{ZK_ROOT_PATH}/computers/{identifier_names['hostname']}/{namespace}/{filename}"
    data = {"testing": "ni-haody"}

    result_data, result_path = save_config(
        namespace=namespace,
        filename=filename,
        data=data,
        identifier_names=identifier_names,
        override=override,
        create_if_missing=create_if_missing,
    )
    assert result_data == data
    assert result_path == path


@pytest.mark.parametrize(
    "namespace, identifier_names, filename",
    [
        pytest.param("new_namespace", {}, "config.yml", id="namespace-missing"),
        pytest.param("software_a", {"hostname": "w10bad"}, "config.yml", id="scope-missing"),
        pytest.param("software_a", {}, "config-bad.yml", id="filename-missing"),
    ],
)
def test_save_config_override_existing_file_return_config_not_found(
    zk_mock, namespace, identifier_names, filename
):
    """
    ConfigNotFoundErrors only occur if user wants to override, and they don't want to create a file
    if it is missing.

    If the user gives a path to a file that they think exists, but it actually doesn't exist, then
    we want to error out since the user explicitly said to override.
    """
    override = True
    create_if_missing = False

    with pytest.raises(ConfigNotFoundError) as err:
        save_config(
            namespace=namespace,
            filename=filename,
            data={},
            identifier_names=identifier_names,
            override=override,
            create_if_missing=create_if_missing,
        )
    assert "not found" in str(err.value)


@pytest.mark.parametrize(
    "filename",
    [
        pytest.param("config.yml", id="namespace-missing"),
        pytest.param("default.yml", id="namespace-missing"),
    ],
)
def test_save_config_file_exists_return_exist_error(zk_mock, filename):
    """
    Config exist errors only occur when config already exists and override is false.

    Does not matter what create-if-missing is since in this scenario the assumption is the file does
    exist and the user wants to add a file but not override anything.
    """
    namespace = "software_a"
    identifier_names = {}
    override = False

    with pytest.raises(ConfigExistsError) as err:
        save_config(
            namespace=namespace,
            filename=filename,
            data={},
            identifier_names=identifier_names,
            override=override,
        )
    assert "already exists" in str(err.value)


def test_save_config_multiple_identifier_names_return_multiple_scopes_error(zk_mock):
    identifier_names = {"hostname": "w11dt000001", "subject_id": "614173"}

    with pytest.raises(MultipleScopeIdentifiersError) as err:
        save_config(
            namespace="software_a",
            filename="config.yml",
            data={"testing": "ni-haody"},
            identifier_names=identifier_names,
        )
    assert "Multiple identifier names" in str(err.value)


def test_save_config_invalid_identifier_names_return_invalid_scope_error(zk_mock):
    identifier_names = {"hostname-typo": "w11dt000001"}

    with pytest.raises(InvalidScopeIdentifierError) as err:
        save_config(
            namespace="software_a",
            filename="config.yml",
            data={"testing": "ni-haody"},
            identifier_names=identifier_names,
        )
    assert "Invalid scope" in str(err.value)


def test_save_config_invalid_data_return_error(zk_mock):
    with pytest.raises(ConfigSerializeError) as err:
        save_config(
            namespace="software_a",
            filename="config_new.yml",
            data={"testing": object()},  # sets are not JSON serializable
            identifier_names={},
        )
    assert "Failed to serialize" in str(err.value)


################################################################################
#
#
#
################################################################################
