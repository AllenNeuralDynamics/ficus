import pytest
from kazoo.exceptions import NoNodeError

from ficus.services.configs import get_config, save_config_file, save_config_obj, _save_config

# _save_config
#   - [x] valid file
#   - valid hostname - default exists
#   - valid hostname - default doesnt exist (should have it)
#   - valid default.yml in default
#   - valid default.yml in hostname
#   - valid default (namespace is non-existing)
#   - valid hostname (namespace + hostname is non-existing)
#   - valid override
#   - valid no override
#   - invalid file (unsupported type)
#   - invalid normal already exists - NO OVERRIDE
#   - invalid default already exists (different because checks json,yml,yaml) - NO OVERRIDE


def test__save_config_defaults(zk_mock):
    path = "/scratch/defaults/software_test/config.yml"
    data = {"testing": "ni-haody"}
    result = _save_config("software_test", "config.yml", data)
    assert result == path
    config = get_config("software_test", "config.yml")
    assert config[0] == data
    assert path in config[1]

def test__save_config_computers(zk_mock):
    """Add a new configuration file into <hostname>/<namespace> where defaults/<namespace> doesn't exist"""
    # TODO: This is saving a configuration file into a new <hostname> with a new <namespace>.
    #       This means a default doesn't exist yet for this <namespace>. Should we allow users to save a new <hostname>
    #       if a default hasn't been given yet? Ask this because behavior of "get_config" is to error when no default
    #       is given, regardless if hostname override exists. However, doing no merge will allow you to grab file.
    # Current assumption is user allowed to create <hostname>/<namespace> regardless of default/<namespace> existing
    namespace = "software_test"
    hostname = "w10test"
    filename = "config.yml"
    path = f"/scratch/computers/{hostname}/{namespace}/{filename}"
    data = {"testing": "ni-haody"}

    result = _save_config(namespace, filename, data, hostname)
    assert result == path

    config = get_config(namespace, filename, hostname, False)
    assert config[0] == data
    assert path in config[1]


# [x] test_get_config
#   - [x] single file (no merge)
#   - [x] default + default.yml
#   - [x] no default + hostname - errors
#   - [x] default + default.yml + hostname + default.yml
#   - [x] invalid namespace
#   - [x] invalid filename
#   - [x] invalid file exists only in default, but tried to look for it in hostname
#   - [x] invalid hostname

# save_config_obj
#   - test dict validation works

# save_config_file
#   - test bytes validation works

# update_config_obj
#   - merge correct
#   - invalid file type
#   - invalid file contents (maybe cant for object)
#   - missing current config (namespace,filename) = what is behavior?
#   - invalid partial_filename = what is behavior?

# update_config_file
#   - merge correct
#   - invalid file type
#   - invalid file contents (maybe cant for object)
#   - missing current config (namespace,filename) = what is behavior?
#   - invalid partial_filename = what is behavior?

# delete config
#   - valid default
#   - valid hostname
#   - invalid doesn't exist

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
