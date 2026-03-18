import pytest

from kazoo.exceptions import NoNodeError

from ficus.crud.zookeeper import get_node, add_node, delete_node


def test_get_node(zk_mock):
    result = get_node(zk_mock, "/scratch/defaults/software_a/config.yml")
    assert result == ({"name": "config", "scope": "default", "default-layer-value": "beep beep"}, [])


def test_get_node_computers(zk_mock):
    result = get_node(zk_mock, "/scratch/computers/w11dt000001/software_a/default.json")
    assert result == ({"computer-default-value": "to rule them all"}, [])


def test_invalid_node_path(zk_mock):
    with pytest.raises(NoNodeError):
        get_node(zk_mock, "/scratch-bad/defaults/software_a/config.yml")


def test_add_node(zk_mock):
    with pytest.raises(NoNodeError):
        get_node(zk_mock, "/scratch/computers/w11dt000001/software_b_test/config.yml")

    add_node(zk_mock, "/scratch/computers/w11dt000001/software_b_test/config.yml", {"test-add": "new data added"})
    result = get_node(zk_mock, "/scratch/computers/w11dt000001/software_b_test/config.yml")
    assert result == ({"test-add": "new data added"}, [])


def test_delete_no_node(zk_mock):
    with pytest.raises(NoNodeError):
        delete_node(zk_mock, "/scratch-bad/computers/w11dt000001/software_b_test/config.yml")


def test_delete_node(zk_mock):
    with pytest.raises(NoNodeError):
        delete_node(zk_mock, "/scratch/computers/w11dt000001/software_b_test/config.yml")

    add_node(zk_mock, "/scratch/computers/w11dt000001/software_b_test/config.yml", {"test-add": "new data added"})
    result = get_node(zk_mock, "/scratch/computers/w11dt000001/software_b_test/config.yml")
    assert result == ({"test-add": "new data added"}, [])

    delete_node(zk_mock, "/scratch/computers/w11dt000001/software_b_test/config.yml")
    with pytest.raises(NoNodeError):
        delete_node(zk_mock, "/scratch/computers/w11dt000001/software_b_test/config.yml")
