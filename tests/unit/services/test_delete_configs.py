import pytest

from kazoo.exceptions import NoNodeError

from ficus.services.configs import delete_config


@pytest.mark.parametrize("hostname", [None, "w11dt000001"])
def test_delete_config(zk_mock, hostname):
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
    namespace = "software_a"
    filename = "DOESNOTEXIST.yml"
    if hostname:
        path = f"/scratch/computers/{hostname}/{namespace}/{filename}"
    else:
        path = f"/scratch/defaults/{namespace}/{filename}"

    with pytest.raises(NoNodeError):
        delete_config(namespace, filename, hostname)


# delete config
#   - [x] valid default
#   - [x] valid hostname
#   - [x] invalid doesn't exist


# [x] test_get_config
#   - [x] single file (no merge)
#   - [x] default + default.yml
#   - [x] no default + hostname - errors
#   - [x] default + default.yml + hostname + default.yml
#   - [x] invalid namespace
#   - [x] invalid filename
#   - [x] invalid file exists only in default, but tried to look for it in hostname
#   - [x] invalid hostname

# _save_config
#   - [x] valid file
#   - [x] valid hostname
#   - [x] valid default.yml in default
#   - [x] valid default.yml in hostname
#   - [x] valid default (namespace is non-existing)
#   - [x] valid hostname (namespace + hostname is non-existing)
#   - [x] valid override
#   - [x] valid no override
#   - [x] invalid file (unsupported type)
#   - [x] invalid normal already exists - NO OVERRIDE
#   - [x] invalid default already exists (different because checks json,yml,yaml) - NO OVERRIDE

# save_config_obj
#   - [x] test valid - good
#   - [x] invalid file type
#   - [x] invalid file content

# save_config_file
#   - [x] test valid - good
#   - [x] invalid file type
#   - [x] invalid file content

# update_config_obj
#   - [x] merge correct defaults
#   - [x] merge correct computers
#   - [x] invalid file type
#   - [x] invalid file contents (maybe cant for object)
#   - [x] missing current config (namespace,filename) = what is behavior?

# update_config_file
#   - [x] merge correct
#   - [x] invalid file contents (maybe cant for object)
#   - [x] missing current config (namespace,filename) = what is behavior?
#   - [x] partial name mismatched with update config type
#   - [x] partial name bad file type


# get all paths
#   - valid (check defaults & hostname was found)
#   - invalid namespace
#   - invalid filename

# get all paths
#   - valid (check defaults & hostname was found)
#   - invalid namespace
#   - invalid hostname

# _merge_configs
#   - valid two good dicts
#   - valid 1 empty prime (main)
#   - valid 1 empty mod (override)
#   - valid override precedence
#   - valid append new keys
#   - valid nested dict (merge these)
