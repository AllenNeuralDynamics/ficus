import logging
import yaml

from fastapi import HTTPException
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError


def get_configs(zk: KazooClient, project_name: str, rig_name: str | None = None) -> dict:
    
    try:
        path = f"/projects/{project_name}/defaults/configuration" 
        data, _ = zk.get(path)
        content = yaml.safe_load(data.decode("utf-8"))
    except NoNodeError:
        raise HTTPException(
            status_code=404,
            detail=f"Project with name {project_name} not found",
        )

    if rig_name: 
        try: 
            rig_path = f"/rigs/{rig_name}/projects/{project_name}/configuration"
            rig_data, _ = zk.get(rig_path)
            rig_content = yaml.safe_load(rig_data.decode("utf-8")) 
            content = deep_merge(content, rig_content)
        except NoNodeError: 
            logging.debug("using default, rig config not found")
            pass
    
    return content


################################################################################
#
#   Utilities 
#
################################################################################


def deep_merge(dict_prime, dict_mod): 
    for key, value in dict_mod.items():
        if isinstance(value, dict):
            if key not in dict_prime:
                dict_prime[key] = type(value)()  # For subclasses of dict
            deep_merge(dict_prime[key], dict_mod[key])
        else:
            dict_prime[key] = value
    return dict_prime

