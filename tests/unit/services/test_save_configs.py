import pytest

from ficus.core.exceptions import (
    ConfigExistsError,
    ConfigNotFoundError,
    ConfigSerializeError,
    InvalidNamespaceError,
    InvalidScopeError,
    InvalidScopeIdentifierError,
    MultipleScopeIdentifiersError,
    UnsupportedFileTypeError,
)
from ficus.services.configs import save_config
from pathlib import Path


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
    data_store, namespace, scope_identifiers, filename, override, create_if_missing
):
    """
    _save_config does most of the bulk work. This unit test is just to ensure the various params
    get converted to (scope/identifier) correctly for _save_config.
    """
    if scope_identifiers == {}:
        path = data_store.rootdir / Path(f"defaults/{namespace}/{filename}")
    else:
        path = data_store.rootdir / Path(f"hostname/{scope_identifiers['hostname']}/{namespace}/{filename}")
    data = {"testing": "ni-haody"}

    result_data, result_path = save_config(
        data_store=data_store,
        namespace=namespace,
        filename=filename,
        data=data,
        scope_identifiers=scope_identifiers,
        override=override,
        create_if_missing=create_if_missing,
    )
    assert result_data == data
    assert result_path == path


def test_save_config_multiple_identifier_names_return_multiple_scopes_error(data_store):
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}

    with pytest.raises(MultipleScopeIdentifiersError):
        save_config(
            data_store=data_store,
            namespace="software_a",
            filename="config.yml",
            data={"testing": "ni-haody"},
            scope_identifiers=scope_identifiers,
        )


def test_save_config_invalid_identifier_names_return_invalid_scope_error(data_store):
    scope_identifiers = {"hostname-typo": "w11dt000001"}

    with pytest.raises(InvalidScopeError):
        save_config(
            data_store=data_store,
            namespace="software_a",
            filename="config.yml",
            data={"testing": "ni-haody"},
            scope_identifiers=scope_identifiers,
        )


def test_save_config_invalid_data_return_error(data_store):
    with pytest.raises(ConfigSerializeError):
        save_config(
            data_store=data_store,
            namespace="software_a",
            filename="config_new.yml",
            data={"testing": object()},
            scope_identifiers={},
        )


def test_save_config_invalid_file_type_return_error(data_store):
    with pytest.raises(UnsupportedFileTypeError):
        save_config(
            data_store=data_store,
            namespace="software_a",
            scope_identifiers={},
            filename="config_new.bad",
            data={},
        )

def test_save_config_override_existing_file_missing_return_config_not_found_error(
    data_store
):
    namespace = "software_a"
    scope_identifiers = {}
    filename = "config-bad.yml"
    override = True
    create_if_missing = False

    with pytest.raises(ConfigNotFoundError):
        save_config(
            data_store=data_store,
            namespace=namespace,
            scope_identifiers=scope_identifiers,
            filename=filename,
            data={},
            override=override,
            create_if_missing=create_if_missing,
        )

def test_save_config_override_existing_wrong_namespace_return_invalid_namespace(
    data_store
):
    namespace = "new namespace"
    scope_identifiers = {}
    filename = "config.yml"
    override = True
    create_if_missing = False

    with pytest.raises(InvalidNamespaceError):
        save_config(
            data_store=data_store,
            namespace=namespace,
            scope_identifiers=scope_identifiers,
            filename=filename,
            data={},
            override=override,
            create_if_missing=create_if_missing,
        )

def test_save_config_override_existing_wrong_scope_id_return_invalid_scope_id(
    data_store
):
    namespace = "new namespace"
    scope_identifiers = {"hostname": "w10bad"}
    filename = "config.yml"
    override = True
    create_if_missing = False

    with pytest.raises(InvalidScopeIdentifierError):
        save_config(
            data_store=data_store,
            namespace=namespace,
            scope_identifiers=scope_identifiers,
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
def test_save_config_file_exists_return_exist_error(data_store, filename):
    """
    Config exist errors only occur when config already exists and override is false.

    Does not matter what create-if-missing is since in this scenario the assumption is the file does
    exist and the user wants to add a file but not override anything.
    """
    namespace = "software_a"

    with pytest.raises(ConfigExistsError):
        save_config(
            data_store=data_store,
            namespace=namespace,
            filename=filename,
            scope_identifiers={},
            data={},
        )
