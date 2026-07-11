import pytest

from ficus.core.exceptions import (
    ConfigMutatedError,
    ConfigNotFoundError,
    ConfigSerializeError,
    InvalidNamespaceError,
    InvalidScopeError,
    InvalidScopeIdentifierError,
    MultipleScopeIdentifiersError
)
from ficus.services.configs import get_config, update_config, update_config_deep
from pathlib import Path


################################################################################
#
#   update_config()
#
################################################################################


def test_update_config_no_identifier_names_return_data_and_path(data_store):
    namespace = "software_a"
    scope_identifier = {}
    mode = "config"
    path = data_store.rootdir / Path(f"defaults/{namespace}/{mode}.yml")

    update_data = {"name": "new name", "testing": "ni-haody"}
    result_data, result_path = update_config(data_store=data_store,
                                             namespace=namespace,
                                             mode=mode,
                                             data=update_data,
                                             scope_identifier=scope_identifier)
    assert result_data == {
        "name": "new name",  # override
        "scope": "default",  # from defaults/config.yml
        "default-layer-value": "beep beep",  # from defaults/config.yml
        "testing": "ni-haody",
    }
    assert result_path == path


def test_update_config_with_identifier_names_return_data_and_path(data_store):
    namespace = "software_a"
    scope_identifier = {"hostname": "w11dt000001"}
    mode = "config"
    path = data_store.rootdir / Path(f"hostname/{scope_identifier['hostname']}/{namespace}/{mode}.yml")

    update_data = {"scope": "w11dt000001new", "testing": "ni-haody"}
    result_data, result_path = update_config(data_store=data_store,
                                             namespace=namespace,
                                             mode=mode,
                                             data=update_data,
                                             scope_identifier=scope_identifier)
    assert result_data == {
        "scope": "w11dt000001new",  # override
        "computer-layer-value": "boop boop",  # from hostname/w11dt000001/config.yml
        "testing": "ni-haody",
    }
    assert result_path == path


def test_update_config_multi_identifiers_return_multiple_scope_identifiers_error(data_store):
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"
    update_data = {"scope": "w11dt000001new", "testing": "ni-haody"}

    with pytest.raises(MultipleScopeIdentifiersError):
        update_config(data_store=data_store,
                      namespace=namespace,
                      mode=mode,
                      data=update_data,
                      scope_identifier=scope_identifiers)


def test_update_config_invalid_identifiers_return_invalid_scope_error(data_store):
    namespace = "software_a"
    scope_identifier = {"fakefake": "w11dt000001"}
    mode = "config"
    update_data = {"scope": "w11dt000001new", "testing": "ni-haody"}

    with pytest.raises(InvalidScopeError):
        update_config(data_store=data_store,
                      namespace=namespace,
                      mode=mode,
                      data=update_data,
                      scope_identifier=scope_identifier)


def test_update_config_missing_namespace_return_invalid_namespace_error(data_store):
    namespace = "new_namespace"
    scope_identifier = {}
    mode="config"
    with pytest.raises(InvalidNamespaceError):
        update_config(data_store=data_store,
                      namespace=namespace,
                      mode=mode,
                      data={},
                      scope_identifier=scope_identifier)


def test_update_config_invalid_scope_id_return_invalid_scope_identifier_error(data_store):
    namespace = "software_a"
    scope_identifier = {"hostname": "w11new"}
    mode="config"
    with pytest.raises(InvalidScopeIdentifierError):
        update_config(data_store=data_store,
                      namespace=namespace,
                      mode=mode,
                      data={},
                      scope_identifier=scope_identifier)


def test_update_config_missing_file_return_config_not_found_error(data_store):
    namespace = "software_a"
    scope_identifier = {}
    mode="config_new"
    with pytest.raises(ConfigNotFoundError):
        update_config(data_store=data_store,
                      namespace=namespace,
                      mode=mode,
                      data={},
                      scope_identifier=scope_identifier)


def test_update_config_invalid_data_yaml_return_config_serialize_error(data_store):
    namespace = "software_a"
    scope_identifier = {}
    mode = "config"
    update_data = {"testing": object()}  # not JSON serializable

    with pytest.raises(ConfigSerializeError):
        update_config(data_store=data_store,
                      namespace=namespace,
                      mode=mode,
                      data=update_data,
                      scope_identifier=scope_identifier)


def test_update_config_invalid_data_json_return_config_serialize_error(data_store):
    namespace = "software_a"
    scope_identifier = {"hostname": "w11dt000001"}
    mode = "default"
    update_data = {"testing": object()}  # not JSON serializable

    with pytest.raises(ConfigSerializeError):
        update_config(data_store=data_store,
                      namespace=namespace,
                      mode=mode,
                      data=update_data,
                      scope_identifier=scope_identifier)


################################################################################
#
#   update_config_deep()
#
################################################################################


def test_update_config_deep_modifies_field_at_its_source_scope(data_store):
    """Updating a scoped field writes back only to the scope that owns it."""
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"
    update_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        data={"computer-layer-value": "to grill them all"},
    )
    # The hostname config.yml owns computer-layer-value and is rewritten.
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"hostname": "w11dt000001"},
                           mode=mode, merge=False)
    assert config == {"computer-layer-value": "to grill them all"}
    # The default scope default.yml is untouched.
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           mode="default", merge=False)
    assert config == {"default-default-value": "the one ring"}


def test_update_config_deep_new_field_without_append_raises(data_store):
    """A field not present anywhere in the override stack raises unless it is
    explicitly appended to the lowest scope."""
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"
    with pytest.raises(ConfigMutatedError):
        update_config_deep(
            data_store=data_store,
            namespace=namespace,
            scope_identifiers=scope_identifiers,
            mode=mode,
            data={"brand_new_field": "ni-haody"},
            append_new_fields_to_last_scope=False,  # default
        )


def test_update_config_deep_new_field_appended_to_lowest_scope(data_store):
    """A new field is written to the lowest priority scope when appending is
    enabled."""
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"
    update_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        data={"brand_new_field": "ni-haody"},
        append_new_fields_to_last_scope=True,
    )
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           scope_identifiers={"subject_id": "614173"},
                           mode=mode, merge=False)
    assert config.get("brand_new_field") == "ni-haody"


def test_update_config_deep_restrict_overriding_defaults(data_store):
    """By default, a value sourced from default.yml is redirected to the mode
    config at the same scope instead of mutating default.yml."""
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"
    update_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        data={"default-default-value": "the one ring to rule them all"},
    )
    # default.yml at the default scope is unchanged.
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           mode="default", merge=False)
    assert config == {"default-default-value": "the one ring"}
    # The value is redirected to config.yml at the default scope.
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           mode=mode, merge=False)
    assert config == {"default-default-value": "the one ring to rule them all"}


def test_update_config_deep_enable_overriding_defaults(data_store):
    """With overwrite_defaults=True, default.yml is updated in place."""
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"
    update_config_deep(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        data={"default-default-value": "the one ring to rule them all"},
        overwrite_defaults=True,
    )
    config, _ = get_config(data_store=data_store, namespace=namespace,
                           mode="default", merge=False)
    assert config == {"default-default-value": "the one ring to rule them all"}

