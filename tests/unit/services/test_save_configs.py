import pytest
from kazoo.exceptions import NoNodeError

from ficus.services.configs import get_config, save_config_file, save_config_obj, _save_config

# _save_config
#   - valid file
#   - valid hostname (override)
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
