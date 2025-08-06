def test_get_configs(zk_client, api_prefix):
    response = zk_client.get(f"{api_prefix}/configs/projects/test_project")
    config = response.json()["output"]
    assert response.status_code == 200
    assert config == {'test_key_default': "test_value_default"}


def test_get_configs_project_and_rig(zk_client, api_prefix):
    response = zk_client.get(f"{api_prefix}/configs/projects/test_project?rig_name=test_rig")
    config = response.json()["output"]
    assert response.status_code == 200
    assert config == {"test_key_default": "test_value_default", "test_key_rig": "test_value_rig"}


def test_get_configs_missing_rig(zk_client, api_prefix):
    response = zk_client.get(f"{api_prefix}/configs/projects/test_project?rig_name=test_bad_rig")
    config = response.json()["output"]
    assert response.status_code == 200
    assert config == {'test_key_default': "test_value_default"}


def test_get_configs_missing_project(zk_client, api_prefix):
    response = zk_client.get(f"{api_prefix}/configs/projects/test_bad_project")
    assert response.status_code == 404
    assert response.json()['detail'] == 'Project with name test_bad_project not found'
