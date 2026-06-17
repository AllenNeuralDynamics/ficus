import pytest

from kazoo.exceptions import NoNodeError

from ficus.crud.zookeeper import get_node, add_node, delete_node
from tests.constants import ZK_ROOT_NODE, ZK_ROOT_PATH


def test_get_node(zk_mock):
    result = get_node(zk_mock, f"{ZK_ROOT_PATH}/defaults/software_a/config.yml")
    assert result == (
        {"name": "config", "scope": "default", "default-layer-value": "beep beep"},
        [],
    )


def test_get_node_computers(zk_mock):
    result = get_node(zk_mock, f"{ZK_ROOT_PATH}/hostname/w11dt000001/software_a/default.json")
    assert result == ({"computer-default-value": "to rule them all"}, [])


def test_invalid_get_node_path(zk_mock):
    with pytest.raises(NoNodeError):
        get_node(zk_mock, f"/{ZK_ROOT_NODE}-bad/defaults/software_a/config.yml")


def test_add_node(zk_mock, encode_data):
    with pytest.raises(NoNodeError):
        get_node(zk_mock, f"{ZK_ROOT_PATH}/hostname/w11dt000001/software_b_test/config.yml")

    add_node(
        zk_mock,
        f"{ZK_ROOT_PATH}/hostname/w11dt000001/software_b_test/config.yml",
        encode_data({"test-add": "new data added"}),
    )
    result = get_node(zk_mock, f"{ZK_ROOT_PATH}/hostname/w11dt000001/software_b_test/config.yml")
    assert result == ({"test-add": "new data added"}, [])


def test_add_node_invalid(zk_mock):
    with pytest.raises(NoNodeError):
        get_node(zk_mock, f"{ZK_ROOT_PATH}/hostname/w11dt000001/software_b_test/config.yml")

    with pytest.raises(TypeError):
        add_node(
            zk_mock,
            f"{ZK_ROOT_PATH}/hostname/w11dt000001/software_b_test/config.yml",
            {"test-add": "new data added"},  # not bytes
        )


def test_delete_no_node(zk_mock):
    with pytest.raises(NoNodeError):
        delete_node(
            zk_mock, f"/{ZK_ROOT_NODE}-bad/hostname/w11dt000001/software_b_test/config.yml"
        )


def test_delete_node(zk_mock, encode_data):
    with pytest.raises(NoNodeError):
        delete_node(zk_mock, f"{ZK_ROOT_PATH}/hostname/w11dt000001/software_b_test/config.yml")

    add_node(
        zk_mock,
        f"{ZK_ROOT_PATH}/hostname/w11dt000001/software_b_test/config.yml",
        encode_data({"test-add": "new data added"}),
    )
    result = get_node(zk_mock, f"{ZK_ROOT_PATH}/hostname/w11dt000001/software_b_test/config.yml")
    assert result == ({"test-add": "new data added"}, [])

    delete_node(zk_mock, f"{ZK_ROOT_PATH}/hostname/w11dt000001/software_b_test/config.yml")
    with pytest.raises(NoNodeError):
        delete_node(zk_mock, f"{ZK_ROOT_PATH}/hostname/w11dt000001/software_b_test/config.yml")
