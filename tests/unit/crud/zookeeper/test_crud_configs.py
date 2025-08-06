import pytest

from fastapi.exceptions import HTTPException
from kazoo.exceptions import NoNodeError

from calibration_api.crud.zookeeper.configs import get_configs


def test_get_configs_project_only(zk_mock):
    result = get_configs(zk_mock, "test_project")

    # Make sure the path was built correctly
    zk_mock.get.assert_called_once_with("/projects/test_project/defaults/configuration")

    # Make sure the return value is correct
    assert result == {"test_key_default": "test_value_default"}


def test_get_configs_project_and_rig(zk_mock):
    result = get_configs(zk_mock, "test_project", "test_rig")

    # Make sure two calls were made (one for default config, one for rig config)
    assert zk_mock.get.call_count == 2

    # Make sure the paths were built correctly
    zk_mock.get.assert_any_call("/projects/test_project/defaults/configuration")
    zk_mock.get.assert_any_call("/rigs/test_rig/projects/test_project/configuration")

    # Make sure the configurations were merged together
    assert result == {"test_key_default": "test_value_default", "test_key_rig": "test_value_rig"}

def test_get_configs_no_rigs(zk_mock):
    result = get_configs(zk_mock, "test_project", "test_bad_rig")

    # Make sure two calls were made (one for default config, one for rig config)
    assert zk_mock.get.call_count == 2

    # Make sure the paths were built correctly
    zk_mock.get.assert_any_call("/projects/test_project/defaults/configuration")
    zk_mock.get.assert_any_call("/rigs/test_bad_rig/projects/test_project/configuration")

    # Make sure only default data was returned
    assert result == {"test_key_default": "test_value_default"}

def test_get_configs_no_project(zk_mock):
    # Make sure only default data was returned
    with pytest.raises(HTTPException) as exception:
        get_configs(zk_mock, "test_bad_project")

    assert exception.value.status_code == 404
    assert exception.value.detail == "Project with name test_bad_project not found"
