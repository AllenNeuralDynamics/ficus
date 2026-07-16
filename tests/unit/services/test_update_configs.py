import pytest

from ficus.core.exceptions import (
    ConfigMutatedError,
)
from ficus.services.configs import update_config

from ficus.services.file_crud import read_file_data


################################################################################
#
#   update_config()
#
################################################################################


def test_update_config_modifies_field_at_its_source_scope(data_store):
    """Updating a scoped field writes back only to the scope that owns it."""
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"
    update_config(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        data={"computer-layer-value": "to grill them all"},
    )
    # The hostname config.yml owns computer-layer-value and is rewritten.
    data = read_file_data(data_store=data_store, namespace=namespace,
                           scope="hostname",
                           scope_identifier="w11dt000001",
                           mode=mode)
    assert data == {"computer-layer-value": "to grill them all"}
    # The default scope default.yml is untouched.
    default_data = read_file_data(data_store=data_store, namespace=namespace,
                                  mode="default")
    assert default_data == {"default-default-value": "the one ring"}


def test_update_config_new_field_without_append_raises(data_store):
    """A field not present anywhere in the override stack raises unless it is
    explicitly appended to the lowest scope."""
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"
    with pytest.raises(ConfigMutatedError):
        update_config(
            data_store=data_store,
            namespace=namespace,
            scope_identifiers=scope_identifiers,
            mode=mode,
            data={"brand_new_field": "ni-haody"},
            append_new_fields_to_last_scope=False,  # default
        )


def test_update_config_new_field_appended_to_lowest_scope(data_store):
    """A new field is written to the lowest priority scope when appending is
    enabled."""
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"
    update_config(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        data={"brand_new_field": "ni-haody"},
        append_new_fields_to_last_scope=True,
    )
    data = read_file_data(data_store=data_store, namespace=namespace,
                           scope="subject_id", scope_identifier="614173",
                           mode=mode)
    assert data.get("brand_new_field") == "ni-haody"


def test_update_config_restrict_overriding_defaults(data_store):
    """By default, a value sourced from default.yml is redirected to the mode
    config at the same scope instead of mutating default.yml."""
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"
    update_config(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        data={"default-default-value": "the one ring to rule them all"},
    )
    # default.yml at the default scope is unchanged.
    data = read_file_data(data_store=data_store, namespace=namespace,
                           mode="default")
    assert data == {"default-default-value": "the one ring"}
    # The value is redirected to config.yml at the default scope.
    data = read_file_data(data_store=data_store, namespace=namespace,
                           mode=mode)
    assert data == {"default-default-value": "the one ring to rule them all"}


def test_update_config_enable_overriding_defaults(data_store):
    """With overwrite_defaults=True, default.yml is updated in place."""
    namespace = "software_a"
    scope_identifiers = {"hostname": "w11dt000001", "subject_id": "614173"}
    mode = "config"
    update_config(
        data_store=data_store,
        namespace=namespace,
        scope_identifiers=scope_identifiers,
        mode=mode,
        data={"default-default-value": "the one ring to rule them all"},
        overwrite_defaults=True,
    )
    data = read_file_data(data_store=data_store, namespace=namespace,
                           mode="default")
    assert data == {"default-default-value": "the one ring to rule them all"}

