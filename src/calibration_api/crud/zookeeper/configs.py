import json
import logging
import yaml

from fastapi import HTTPException
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError


def get_configs(zk: KazooClient, project_name: str, rig_name: str | None = None) -> dict | str:
    try:
        path = f"/projects/{project_name}/defaults/configuration" 
        content = get_zk_node(zk, path)
    except NoNodeError:
        raise HTTPException(
            status_code=404,
            detail=f"Project with name {project_name} not found",
        )

    # Deep merge with rig-specific configuration if filetype is yaml or json
    if rig_name: 
        try: 
            rig_path = f"/rigs/{rig_name}/projects/{project_name}/configuration"
            rig_content = get_zk_node(zk, rig_path)
            if isinstance(rig_content, dict):
                content = deep_merge(content, rig_content)
            else: 
                logging.debug(f"Cannot merge rig config for {rig_name} not a valid format (yaml or json) \
                                Using rig config as is (overrides defaults)")
                content = rig_content
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

def get_zk_node(zk: KazooClient, path: str): 
    data, _ = zk.get(path)
    decoded_data = data.decode("utf-8")
    try: 
        content = yaml.safe_load(decoded_data)
    except yaml.YAMLError as e: 
        logging.error(f"Failed to decode file as YAML for node @ {path}: {e}")
        try:
            content = json.loads(decoded_data)
        except json.JSONDecodeError as e: 
            logging.error(f"Failed to decode file as JSON for node @ {path}: {e}")
            content = decoded_data
    return content
