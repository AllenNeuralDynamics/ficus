import pytest

from kazoo.exceptions import NoNodeError

from ficus.services.configs import delete_config


"""
NOTE: Some tests are parameterized to test deleting configurations to the following: 
        1. /defaults/... path where default configurations live
        2. /computers/... path where override configurations live
    This is determined by whether a hostname is given or not. 
"""


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test_delete_config(zk_mock, hostname):
    """Test delete config file"""
    namespace = "software_a"
    filename = "config.yml"
    if hostname:
        path = f"/scratch/computers/{hostname}/{namespace}/{filename}"
    else:
        path = f"/scratch/defaults/{namespace}/{filename}"

    result = delete_config(namespace, filename, hostname)
    assert path == result
    assert not zk_mock.exists(path)


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test_delete_config_missing_file(zk_mock, hostname):
    """Test delete config file that doesn't exist"""
    namespace = "software_a"
    filename = "DOESNOTEXIST.yml"
    if hostname:
        path = f"/scratch/computers/{hostname}/{namespace}/{filename}"
    else:
        path = f"/scratch/defaults/{namespace}/{filename}"

    with pytest.raises(NoNodeError):
        delete_config(namespace, filename, hostname)
