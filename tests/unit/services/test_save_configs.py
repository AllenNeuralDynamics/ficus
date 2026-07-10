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
from ficus.services.configs import VALID_EXTENSIONS, get_config, save_config, save_config_deep
from pathlib import Path


################################################################################
#
#   save_config()
#
################################################################################
@pytest.mark.parametrize(
    "namespace, scope_identifiers, mode, suffix, overwrite",
    [
        pytest.param("new_namespace", {}, "config", ".yml", False, id="save-new-namespace"),
        pytest.param("new_namespace", {}, "default", ".yml", False, id="save-new-default-file"),
        pytest.param("software_a", {}, "config_new", ".yml", False, id="save-new-file"),
        pytest.param("software_a", {}, "config", ".json", True, id="save-change_format"),
        pytest.param(
            "software_a", {"hostname": "w11new"}, "config", ".yml", False, id="save-new-scope"
        ),
        pytest.param(
            "software_a", {}, "config", ".yml", True, id="overwrite-existing"
        ),
    ],
)
def test_save_config_valid_return_data_and_path(
    data_store, namespace, scope_identifiers, mode, suffix, overwrite
):
    filename = f"{mode}{suffix}"
    if scope_identifiers == {}:
        path = data_store.rootdir / Path(f"defaults/{namespace}/{filename}")
    else:
        path = data_store.rootdir / Path(f"hostname/{scope_identifiers['hostname']}/{namespace}/{filename}")
    data = {"testing": "ni-haody"}

    result_data, result_path = save_config(
        data_store=data_store,
        namespace=namespace,
        scope_identifier=scope_identifiers,
        mode=mode,
        suffix=suffix,
        data=data,
        overwrite=overwrite,
    )
    assert result_data == data
    assert result_path == path




def test_save_config_invalid_identifier_names_return_invalid_scope_error(data_store):
    scope_identifiers = {"hostname-typo": "w11dt000001"}

    with pytest.raises(InvalidScopeError):
        save_config(
            data_store=data_store,
            namespace="software_a",
            mode="config",
            data={"testing": "ni-haody"},
            scope_identifier=scope_identifiers,
        )


def test_save_config_invalid_data_return_error(data_store):
    with pytest.raises(ConfigSerializeError):
        save_config(
            data_store=data_store,
            namespace="software_a",
            mode="config_new",
            data={"testing": object()},
            scope_identifier={},
        )


def test_save_config_invalid_file_type_return_error(data_store):
    with pytest.raises(UnsupportedFileTypeError):
        save_config(
            data_store=data_store,
            namespace="software_a",
            scope_identifier={},
            mode="config_new",
            suffix=".bad",
            data={},
        )


def test_save_config_overwrite_existing_wrong_namespace_return_invalid_namespace(
    data_store
):
    namespace = "new namespace"
    scope_identifiers = {}
    mode = "config"
    overwrite = True
    create_missing_namespace = False

    with pytest.raises(InvalidNamespaceError):
        save_config(
            data_store=data_store,
            namespace=namespace,
            scope_identifier=scope_identifiers,
            mode=mode,
            data={},
            overwrite=overwrite,
            create_missing_namespace=create_missing_namespace,
        )


@pytest.mark.parametrize(
    "mode",
    [
        pytest.param("config", id="namespace-missing"),
        pytest.param("default", id="namespace-missing"),
    ],
)
def test_save_config_file_exists_return_exist_error(data_store, mode):
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
            mode=mode,
            scope_identifier={},
            data={},
        )

def test_save_config_change_suffix(data_store):
    ... # TODO:

################################################################################
#
#   save_config() create_missing_* options
#
################################################################################
@pytest.mark.parametrize(
    "namespace, scope_identifier, kwargs, exception",
    [
        pytest.param(
            "new_namespace", {}, {"create_missing_namespace": False},
            InvalidNamespaceError, id="no-create-namespace",
        ),
        pytest.param(
            "software_a", {"hostname": "w11new"}, {"create_missing_scope_id": False},
            InvalidScopeIdentifierError, id="no-create-scope-id",
        ),
        pytest.param(
            "software_a", {"rig_id": "rig1"}, {},
            InvalidScopeError, id="no-create-scope-default",
        ),
        pytest.param(
            "software_a", {"rig_id": "rig1"},
            {"create_missing_scope": True, "create_missing_scope_id": False},
            InvalidScopeIdentifierError, id="create-scope-but-not-scope-id",
        ),
    ],
)
def test_save_config_missing_path_flags_raise(
    data_store, namespace, scope_identifier, kwargs, exception
):
    """Disabling a create_missing_* flag raises when the corresponding path is
    missing from the data store."""
    with pytest.raises(exception):
        save_config(
            data_store=data_store,
            namespace=namespace,
            scope_identifier=scope_identifier,
            mode="config",
            data={"testing": "ni-haody"},
            **kwargs,
        )


def test_save_config_create_missing_scope(data_store):
    """A brand new scope is created and the config saved when
    create_missing_scope is True."""
    namespace = "software_a"
    scope_identifier = {"rig_id": "rig1"}
    data = {"testing": "ni-haody"}
    expected_path = data_store.rootdir / Path("rig_id/rig1/software_a/config.yml")
    assert not data_store.exists(expected_path)

    result_data, result_path = save_config(
        data_store=data_store,
        namespace=namespace,
        scope_identifier=scope_identifier,
        mode="config",
        data=data,
        create_missing_scope=True,
    )
    assert result_data == data
    assert result_path == expected_path
    assert data_store.exists(expected_path)

################################################################################
#
#   save_config_deep()
#
################################################################################
def test_deep_save_multiple_scopes_no_changes(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "newnewnew", "subject_id": "614173"}
    mode="config"
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, mode=mode)
    # overwrite_defaults=False, but not changes were made to default.yml.
    # override stack will include default.yml, but since no changes were made at
    # this scope, default.yml should be unchanged.
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        data=config,
    )

def test_deep_save_new_namespace(data_store):
    namespace="new_namespace"
    scope_identifiers = {"hostname": "newnewnew", "subject_id": "614173"}
    mode="config"
    # config, _ = get_config(data_store=data_store, namespace=namespace,
    #                        scope_identifiers=scope_identifiers, mode=mode)
    config = {"testing": "ni-haody"}
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        data=config,
        create_missing_namespace=True,
        append_new_fields_to_last_scope=True,
    )

def test_deep_save_new_namespace_raises(data_store):
    namespace="new_namespace"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode="config"
    # config, _ = get_config(data_store=data_store, namespace=namespace,
    config = {"testing": "ni-haody"}
    with pytest.raises(InvalidNamespaceError):
        save_config_deep(
            data_store=data_store,
            namespace=namespace,
            scope_identifiers=scope_identifiers,
            mode=mode,
            data=config,
            create_missing_namespace=False
        )

def test_deep_save_restrict_adding_new_field(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode="config"
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, mode=mode)
    config.update({"testing": "ni-haody"})
    with pytest.raises(ConfigMutatedError):
        save_config_deep(
            data_store=data_store,
            namespace=namespace,
            mode=mode,
            data=config,
            scope_identifiers=scope_identifiers,
            append_new_fields_to_last_scope=False  # default value
        )


def test_deep_save_add_new_field_to_lowest_scope(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode="config"
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, mode=mode)
    config.update({"testing": "ni-haody"})
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        mode=mode,
        data=config,
        scope_identifiers=scope_identifiers,
        append_new_fields_to_last_scope=True
    )
    # Fetch config.yml from default scope. It should have new fields not present
    # in the original.
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, mode=mode,
                           merge=False)
    assert "testing" in config and config["testing"] == "ni-haody"


def test_deep_save_multiple_scopes_restrict_overriding_defaults(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode="config"
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, mode=mode)
    # This value comes from default.yml in scope=default.
    config["default-default-value"] = "the one ring to rule them all"
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        data=config,
    )
    # Fetch default.yml from default scope. It should be unchanged.
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           mode="default", merge=False)
    assert config == {"default-default-value": "the one ring"}
    # Fetch config.yml from default scope. It should have values that came
    # from default.yml
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           mode=mode, merge=False)
    assert config == {"default-default-value": "the one ring to rule them all"}


def test_deep_save_multiple_scopes_enable_overriding_defaults(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode="config"
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, mode=mode)
    config["default-default-value"] = "the one ring to rule them all"
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        data=config,
        overwrite_defaults=True
    )
    # Fetch default.yml from default scope. It should have new values.
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           mode="default", merge=False)
    assert config == {"default-default-value": "the one ring to rule them all"}


def test_deep_save_multiple_scopes_no_changes_check_all_cfgs(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode="config"
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, mode=mode)
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        data=config,
    )
    # Fetch all unmerged configs.
    # Fetch default.yml from default scope. It should have new values.
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           mode="default", merge=False)
    assert config == {"default-default-value": "the one ring"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           mode=mode, merge=False)
    assert config == {"name": "config", "scope": "default", "default-layer-value": "beep beep"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"hostname": "w11dt000001"},
                           mode="default", merge=False)
    assert config == {"computer-default-value": "to rule them all"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"hostname": "w11dt000001"},
                           mode=mode, merge=False)
    assert config == {"computer-layer-value": "boop boop"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"subject_id": "614173"},
                           mode="default", merge=False)
    assert config == {"subject-default-value": "one config to bring them all"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"subject_id": "614173"},
                           mode=mode, merge=False)
    assert config == {"subject-layer-value": "bap bap", "scope": "614173",
                      "The Cure": "show me how you do that trick"}

def test_deep_save_multiple_scopes_many_changes_check_all_cfgs(data_store):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode="config"
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, mode=mode)
    config["name"] = "my config"
    config["computer-layer-value"] = "to grill them all"
    config["subject-layer-value"] = "bebop"
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        data=config,
    )
    # Fetch all unmerged configs.
    # Fetch default.yml from default scope. It should have new values.
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           mode="default", merge=False)
    assert config == {"default-default-value": "the one ring"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           mode=mode, merge=False)
    assert config == {"name": "my config", "scope": "default", "default-layer-value": "beep beep"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"hostname": "w11dt000001"},
                           mode="default", merge=False)
    assert config == {"computer-default-value": "to rule them all"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"hostname": "w11dt000001"},
                           mode=mode, merge=False)
    assert config == {"computer-layer-value": "to grill them all"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"subject_id": "614173"},
                           mode="default", merge=False)
    assert config == {"subject-default-value": "one config to bring them all"}
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"subject_id": "614173"},
                           mode=mode, merge=False)
    assert config == {"subject-layer-value": "bebop", "scope": "614173",
                      "The Cure": "show me how you do that trick"}

@pytest.mark.parametrize("new_suffix", VALID_EXTENSIONS)
def test_deep_save_changing_suffix(data_store, new_suffix):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"
    config, old_paths = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, mode=mode)
    config["name"] = "my config"
    config["computer-layer-value"] = "to grill them all"
    config["subject-layer-value"] = "bebop"
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        suffix=new_suffix,
        data=config,
    )

    config, paths = get_config(data_store=data_store, namespace=namespace,
                               scope_identifiers=scope_identifiers, mode=mode)
    
    for old_path, new_path in zip(old_paths, paths):
        tmp_mode = old_path.stem
        if tmp_mode == mode:
            assert old_path.with_suffix(new_suffix) == new_path
        else:
            assert old_path == new_path

@pytest.mark.parametrize("new_suffix", VALID_EXTENSIONS)
def test_deep_save_changing_suffix_no_changes(data_store, new_suffix):
    namespace="software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"
    config, old_paths = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers=scope_identifiers, mode=mode)
    save_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        suffix=new_suffix,
        data=config,
    )

    config, paths = get_config(data_store=data_store, namespace=namespace,
                               scope_identifiers=scope_identifiers, mode=mode)
    
    for old_path, new_path in zip(old_paths, paths):
        tmp_mode = old_path.stem
        if tmp_mode == mode:
            assert old_path.with_suffix(new_suffix) == new_path
        else:
            assert old_path == new_path
