import pytest

from ficus.core.exceptions import (
    ConfigNotFoundError,
    ConfigSerializeError,
    InvalidScopeIdentifierError,
    MultipleScopeIdentifiersError,
)
from ficus.services.configs import update_config
from tests.constants import ZK_ROOT_PATH


################################################################################
#
#   update_config()
#
################################################################################


def test_update_config_no_identifier_names_return_data_and_path(zk_mock):
    namespace = "software_a"
    identifier_names = {}
    filename = "config.yml"
    path = f"{ZK_ROOT_PATH}/defaults/{namespace}/{filename}"

    update_data = {"name": "new name", "testing": "ni-haody"}
    result_data, result_path = update_config(namespace, filename, update_data, identifier_names)
    assert result_data == {
        "name": "new name",  # override
        "scope": "default",  # from defaults/config.yml
        "default-layer-value": "beep beep",  # from defaults/config.yml
        "testing": "ni-haody",
    }
    assert result_path == path


def test_update_config_with_identifier_names_return_data_and_path(zk_mock):
    namespace = "software_a"
    identifier_names = {"hostname": "w11dt000001"}
    filename = "config.yml"
    path = f"{ZK_ROOT_PATH}/computers/{identifier_names['hostname']}/{namespace}/{filename}"

    update_data = {"scope": "w11dt000001new", "testing": "ni-haody"}
    result_data, result_path = update_config(namespace, filename, update_data, identifier_names)
    assert result_data == {
        "scope": "w11dt000001new",  # override
        "computer-layer-value": "boop boop",  # from computers/w11dt000001/config.yml
        "testing": "ni-haody",
    }
    assert result_path == path


def test_update_config_multi_identifiers_return_multiple_scope_identifiers_error(zk_mock):
    namespace = "software_a"
    identifier_names = {"hostname": "w11dt000001", "subject_id": "614173"}
    filename = "config.yml"
    update_data = {"scope": "w11dt000001new", "testing": "ni-haody"}

    with pytest.raises(MultipleScopeIdentifiersError):
        update_config(namespace, filename, update_data, identifier_names)


def test_update_config_invalid_identifiers_return_invalid_scope_error(zk_mock):
    namespace = "software_a"
    identifier_names = {"fakefake": "w11dt000001"}
    filename = "config.yml"
    update_data = {"scope": "w11dt000001new", "testing": "ni-haody"}

    with pytest.raises(InvalidScopeIdentifierError):
        update_config(namespace, filename, update_data, identifier_names)


@pytest.mark.parametrize(
    "namespace, identifier_names, filename",
    [
        pytest.param("new_namespace", {}, "config.yml", id="missing-namespace"),
        pytest.param("software_a", {}, "config_new.yml", id="missing-file"),
        pytest.param("software_a", {"hostname": "w11new"}, "config.yml", id="missing-scope"),
    ],
)
def test_update_config_missing_file_return_config_not_found_error(
    zk_mock, namespace, identifier_names, filename
):
    with pytest.raises(ConfigNotFoundError):
        update_config(
            namespace=namespace,
            filename=filename,
            data={},
            identifier_names=identifier_names,
        )


def test_update_config_invalid_data_yaml_return_config_serialize_error(zk_mock):
    namespace = "software_a"
    identifier_names = {}
    filename = "config.yml"
    update_data = {"testing": object()}  # not JSON serializable

    with pytest.raises(ConfigSerializeError):
        update_config(namespace, filename, update_data, identifier_names)


def test_update_config_invalid_data_json_return_config_serialize_error(zk_mock):
    namespace = "software_a"
    identifier_names = {"hostname": "w11dt000001"}
    filename = "default.json"
    update_data = {"testing": object()}  # not JSON serializable

    with pytest.raises(ConfigSerializeError):
        update_config(namespace, filename, update_data, identifier_names)
