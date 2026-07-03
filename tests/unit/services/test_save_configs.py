import pytest

from ficus.core.exceptions import (
    ConfigExistsError,
    ConfigMutatedError,
    ConfigSerializeError,
    InvalidNamespaceError,
    InvalidScopeError,
    InvalidScopeIdentifierError,
    UnsupportedFileTypeError,
)
from ficus.services.configs import get_config, save_config, save_config_deep
from pathlib import Path


################################################################################
#
#   save_config()
#
################################################################################
@pytest.mark.parametrize(
    "namespace, scope_identifiers, filename, override, create_missing_paths",
    [
        pytest.param("new_namespace", {}, "config.yml", False, True, id="save-new-namespace"),
        pytest.param("new_namespace", {}, "default.yml", False, True, id="save-new-default-file"),
        pytest.param("software_a", {}, "config_new.yml", False, True, id="save-new-file"),
        pytest.param(
            "software", {"hostname": "w11new"}, "config.yml", False, True, id="save-new-scope"
        ),
        pytest.param(
            "software_a", {}, "config.yml", True, True, id="override-create-missing-paths"
        ),
        pytest.param(
            "software_a", {}, "config.yml", True, False, id="override-no-create-missing-paths"
        ),
    ],
)
def test_save_config_valid_return_data_and_path(
    data_store, namespace, scope_identifiers, filename, override, create_missing_paths
):
    if scope_identifiers == {}:
        path = data_store.rootdir / Path(f"defaults/{namespace}/{filename}")
    else:
        path = data_store.rootdir / Path(f"hostname/{scope_identifiers['hostname']}/{namespace}/{filename}")
    data = {"testing": "ni-haody"}

    result_data, result_path = save_config(
        data_store=data_store,
        namespace=namespace,
        scope_identifier=scope_identifiers,
        filename=filename,
        data=data,
        override=override,
        create_missing_paths=create_missing_paths
    )
    assert result_data == data
    assert result_path == path




def test_save_config_invalid_identifier_names_return_invalid_scope_error(data_store):
    scope_identifiers = {"hostname-typo": "w11dt000001"}

    with pytest.raises(InvalidScopeError):
        save_config(
            data_store=data_store,
            namespace="software_a",
            filename="config.yml",
            data={"testing": "ni-haody"},
            scope_identifier=scope_identifiers,
        )


def test_save_config_invalid_data_return_error(data_store):
    with pytest.raises(ConfigSerializeError):
        save_config(
            data_store=data_store,
            namespace="software_a",
            filename="config_new.yml",
            data={"testing": object()},
            scope_identifier={},
        )


def test_save_config_invalid_file_type_return_error(data_store):
    with pytest.raises(UnsupportedFileTypeError):
        save_config(
            data_store=data_store,
            namespace="software_a",
            scope_identifier={},
            filename="config_new.bad",
            data={},
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
            scope_identifier=scope_identifiers,
            filename=filename,
            data={},
            override=override,
            create_missing_paths=create_if_missing,
        )


def test_save_config_override_existing_wrong_scope_id_return_invalid_scope_id(
    data_store
):
    namespace = "software_a"
    scope_identifiers = {"hostname": "w10bad"}
    filename = "config.yml"
    override = True
    create_missing_paths = False

    with pytest.raises(InvalidScopeIdentifierError):
        save_config(
            data_store=data_store,
            namespace=namespace,
            scope_identifier=scope_identifiers,
            filename=filename,
            data={},
            override=override,
            create_missing_paths=create_missing_paths,
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
            scope_identifier={},
            data={},
        )


################################################################################
#
#   save_config_deep()
#
################################################################################
def test_deep_save_multiple_scopes_no_changes(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename="config.yml"
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, filename=filename)
    # override_defaults=False, but not changes were made to default.yml.
    # override stack will include default.yml, but since no changes were made at
    # this scope, default.yml should be unchanged.
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        filename=filename,
        data=config,
    )

def test_deep_save_restrict_adding_new_field(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename="config.yml"
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, filename=filename)
    config.update({"testing": "ni-haody"})
    with pytest.raises(ConfigMutatedError):
        save_config_deep(
            data_store=data_store,
            namespace=namespace,
            filename=filename,
            data=config,
            scope_identifiers=scope_identifiers,
            append_new_fields_to_last_scope=False  # default value
        )


def test_deep_save_add_new_field_to_lowest_scope(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename="config.yml"
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, filename=filename)
    config.update({"testing": "ni-haody"})
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        filename=filename,
        data=config,
        scope_identifiers=scope_identifiers,
        append_new_fields_to_last_scope=True
    )
    # Fetch config.yml from default scope. It should have new fields not present
    # in the original.
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, filename=filename,
                           merge=False)
    assert "testing" in config and config["testing"] == "ni-haody"


def test_deep_save_multiple_scopes_restrict_overriding_defaults(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename="config.yml"
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, filename=filename)
    # This value comes from default.yml in scope=default.
    config["default-default-value"] = "the one ring to rule them all"
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        filename=filename,
        data=config,
    )
    # Fetch default.yml from default scope. It should be unchanged.
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           filename="default.yml", merge=False)
    assert config == {"default-default-value": "the one ring"}
    # Fetch config.yml from default scope. It should have values that came
    # from default.yml
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           filename=filename, merge=False)
    assert config == {"default-default-value": "the one ring to rule them all"}


def test_deep_save_multiple_scopes_enable_overriding_defaults(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename="config.yml"
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, filename=filename)
    config["default-default-value"] = "the one ring to rule them all"
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        filename=filename,
        data=config,
        override_defaults=True
    )
    # Fetch default.yml from default scope. It should have new values.
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           filename="default.yml", merge=False)
    assert config == {"default-default-value": "the one ring to rule them all"}


def test_deep_save_multiple_scopes_no_changes_check_all_cfgs(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename="config.yml"
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, filename=filename)
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        filename=filename,
        data=config,
    )
    # Fetch all unmerged configs.
    # Fetch default.yml from default scope. It should have new values.
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           filename="default.yml", merge=False)
    assert config == {"default-default-value": "the one ring"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           filename=filename, merge=False)
    assert config == {"name": "config", "scope": "default", "default-layer-value": "beep beep"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"hostname": "w11dt000001"},
                           filename="default.yml", merge=False)
    assert config == {"computer-default-value": "to rule them all"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"hostname": "w11dt000001"},
                           filename=filename, merge=False)
    assert config == {"computer-layer-value": "boop boop"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"subject_id": "614173"},
                           filename="default.json", merge=False)
    assert config == {"subject-default-value": "one config to bring them all"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"subject_id": "614173"},
                           filename=filename, merge=False)
    assert config == {"subject-layer-value": "bap bap", "scope": "614173",
                      "The Cure": "show me how you do that trick"}

def test_deep_save_multiple_scopes_many_changes_check_all_cfgs(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename="config.yml"
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, filename=filename)
    config["name"] = "my config"
    config["computer-layer-value"] = "to grill them all"
    config["subject-layer-value"] = "bebop"
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        filename=filename,
        data=config,
    )
    # Fetch all unmerged configs.
    # Fetch default.yml from default scope. It should have new values.
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           filename="default.yml", merge=False)
    assert config == {"default-default-value": "the one ring"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           filename=filename, merge=False)
    assert config == {"name": "my config", "scope": "default", "default-layer-value": "beep beep"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"hostname": "w11dt000001"},
                           filename="default.yml", merge=False)
    assert config == {"computer-default-value": "to rule them all"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"hostname": "w11dt000001"},
                           filename=filename, merge=False)
    assert config == {"computer-layer-value": "to grill them all"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"subject_id": "614173"},
                           filename="default.json", merge=False)
    assert config == {"subject-default-value": "one config to bring them all"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"subject_id": "614173"},
                           filename=filename, merge=False)
    assert config == {"subject-layer-value": "bebop", "scope": "614173",
                      "The Cure": "show me how you do that trick"}
