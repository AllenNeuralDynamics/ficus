import json
import yaml

from ficus.crud.zookeeper import get_node, add_node, delete_node
from ficus.database.zookeeper import get_zk_client
from ficus.schemas.configs import ConfigData


DEFAULTS_PATH_PREFIX = "/scratch/defaults"
COMPUTERS_PATH_PREFIX = "/scratch/computers"


def get_config(namespace: str, filename: str, hostname: str | None, merge: bool = True) -> tuple[ConfigData, dict]:
    """Get configs from zookeeper. Handles merging defaults and partial config override.

    :param namespace: namespace to search for file (in default and computers/<hostname>).
    :param filename: name of the file.
    :param hostname: hostname to search for a partial config override.
    :param merge: if true merge default config with partial config override.
    :return: config data and dictionary denoting paths of the partial files used to create the config data
    """
    DEFAULT_PATH = f"{DEFAULTS_PATH_PREFIX}/{namespace}/{filename}"
    COMPUTER_PATH = f"{COMPUTERS_PATH_PREFIX}/{hostname}/{namespace}/{filename}"

    valid_paths = {}

    with get_zk_client() as client:
        config, _children = get_node(client, DEFAULT_PATH)
        if config:
            valid_paths["default"] = DEFAULT_PATH
        if hostname:
            hostname_config, _children = get_node(client, COMPUTER_PATH)
            if hostname_config:
                valid_paths["hostname"] = COMPUTER_PATH
                config = _merge_configs(config, hostname_config) if merge else hostname_config

        return config, valid_paths


def save_config_obj(namespace: str, filename: str, data: dict, hostname: str | None, override: bool = False) -> str:
    """Save data (dictionary) as a config file in zookeeper.
    Saves to defaults if hostname is missing, else it will save to hostname location.

    :param namespace: namespace to save file to.
    :param filename: name of the file.
    :param data: config data as python dictionary
    :param hostname: hostname to save file to.
    :param override: if true and file exists, overwrite the file.
    :returns: path where file was saved.
    """
    data_as_bytes = _validate_and_convert_to_bytes(filename, data)
    return _save_config(namespace=namespace, filename=filename, data=data_as_bytes, hostname=hostname, override=override)


def save_config_file(
    namespace: str, filename: str, data: bytes, hostname: str | None = None, override: bool = False
) -> str:
    """Save data (file as bytes) as a config file in zookeeper.
    Saves to defaults if hostname is missing, else it will save to hostname location.

    :param namespace: namespace to save file to.
    :param filename: name of the file.
    :param data: config data as bytes
    :param hostname: hostname to save file to.
    :param override: if true and file exists, overwrite the file.
    :returns: path where file was saved.
    """
    _validate_and_convert_to_dict(filename, data)  # Throw away value, only want to validate
    return _save_config(namespace=namespace, filename=filename, data=data, hostname=hostname, override=override)


def update_config_object(namespace: str, filename: str, hostname: str | None, data: dict) -> str:
    """Update config file in zookeeper with new data (dictionary)

    :param namespace: namespace to save file to.
    :param filename: name of the file.
    :param hostname: hostname to save file to (indicates config override).
    :param data: config data as python dictionary
    :returns: path where file was updated.
    """
    current_config, _ = get_config(namespace=namespace, filename=filename, hostname=hostname)
    _validate_and_convert_to_bytes(filename="throwaway.json", data=data)  # Throw away value, only want to validate
    raw_config = _merge_configs(current_config, data)
    config = _validate_and_convert_to_bytes(filename, raw_config)
    return _save_config(namespace=namespace, filename=filename, data=config, hostname=hostname, override=True)


def update_config_file(namespace: str, filename: str, partial_filename: str, hostname: str | None, data: bytes) -> str:
    """Update config file in zookeeper with new data (bytes). Due to validation, if the file is a yaml file, it removes
    the comments from the file and reorders the field alphabetically.

    :param namespace: namespace to save file to.
    :param filename: name of the file.
    :param hostname: hostname to save file to (indicates config override).
    :param data: config data as bytes
    :returns: path where file was updated.
    """
    current_config, _ = get_config(namespace=namespace, filename=filename, hostname=hostname)
    new_config = _validate_and_convert_to_dict(partial_filename, data)
    raw_config = _merge_configs(current_config, new_config)
    config = _validate_and_convert_to_bytes(filename, raw_config)
    return _save_config(namespace=namespace, filename=filename, data=config, hostname=hostname, override=True)


def delete_config(namespace: str, filename: str, hostname: str | None) -> str | list[str]:
    """Delete config file from zookeeper. Deletes from defaults/ and computers/<hostname> if hostname is given.

    :param namespace: namespace to save file to.
    :param filename: name of the file.
    :param hostname: hostname to save file to (indicates config override).
    :returns: path where file was deleted.
    """
    DEFAULT_PATH = f"{DEFAULTS_PATH_PREFIX}/{namespace}/{filename}"
    with get_zk_client() as client:
        delete_node(client, DEFAULT_PATH)
        if hostname:
            COMPUTER_PATH = f"{COMPUTERS_PATH_PREFIX}/{hostname}/{namespace}/{filename}"
            delete_node(client, COMPUTER_PATH)
            return [DEFAULT_PATH, COMPUTER_PATH]
    return DEFAULT_PATH


def get_all_paths(namespace: str, filename: str) -> list[str]:
    """Get all paths that contains a specific config file. This includes all partial overrides that make up that config.

    :param namespace: namespace to search for the filename.
    :param filename: name of the file.
    :returns: list of paths containing file.
    """
    all_paths = []
    with get_zk_client() as client:
        # Check if default/namespace/filename exists
        default_subpath = f"{DEFAULTS_PATH_PREFIX}/{namespace}/{filename}"
        if client.exists(default_subpath):
            all_paths.append(default_subpath)

        # Check if computer/hostname/namespace/filename exists for all hostnames
        _, hostnames = get_node(client, COMPUTERS_PATH_PREFIX)
        for hostname in hostnames:
            hostname_subpath = f"{COMPUTERS_PATH_PREFIX}/{hostname}/{namespace}/{filename}"
            if client.exists(hostname_subpath):
                all_paths.append(hostname_subpath)
    return all_paths


def get_all_files(namespace: str, hostname: str | None) -> list[str]:
    """Get all files under a specific namespace. If a specific hostname isn't provided, it returns all files under all
    hostnames with the specified namespace.

    :param namespace: namespace to search get all files.
    :param hostname: if given, search only in this hostname for files under given namespace.
    :returns: list of files within namespace/hostname path.
    """
    all_files = []
    with get_zk_client() as client:

        def collect_files(subpath: str):
            for file in get_node(client, subpath)[1]:
                all_files.append(f"{subpath}/{file}")

        collect_files(f"{DEFAULTS_PATH_PREFIX}/{namespace}")

        hostnames = [hostname] if hostname else get_node(client, COMPUTERS_PATH_PREFIX)[1]
        for h in hostnames:
            collect_files(f"{COMPUTERS_PATH_PREFIX}/{h}/{namespace}")

    return all_files


################################################################################
#
#   Utility
#
################################################################################


def _merge_configs(dict_prime: dict, dict_mod: dict) -> dict:
    """Merge two configuration dictionaries (handles nested dictionaries).

    :param dict_prime: main dictionary which will be overridden and appended to
    :param dict_mod: dictionary with overrides
    :returns: merged configuration
    """
    for key, value in dict_mod.items():
        if isinstance(value, dict):
            if key not in dict_prime:
                dict_prime[key] = type(value)()  # For subclasses of dict
            _merge_configs(dict_prime[key], dict_mod[key])
        else:
            dict_prime[key] = value
    return dict_prime


def _save_config(namespace: str, filename: str, data: bytes, hostname: str | None, override: bool = False) -> str:
    """Helper function to save config file (as bytes, what zookeeper expects).

    :param namespace: namespace to save file to.
    :param filename: name of the file.
    :param data: config data as bytes
    :param hostname: hostname to save file to.
    :param override: if true and file exists, overwrite the file.
    :returns: path where file was saved
    """
    # This function assumes that data has already been validated
    if hostname:
        CONFIG_PATH = f"{COMPUTERS_PATH_PREFIX}/{hostname}/{namespace}/{filename}"
    else:
        CONFIG_PATH = f"{DEFAULTS_PATH_PREFIX}/{namespace}/{filename}"

    with get_zk_client() as client:
        if not override and client.exists(CONFIG_PATH):
            raise FileExistsError(f"File already exists: {CONFIG_PATH}")

        add_node(client, CONFIG_PATH, data)

    return CONFIG_PATH


def _validate_and_convert_to_bytes(filename: str, data: dict) -> bytes:
    """Validates filename based on extension and converts data into bytes.

    :param filename: name of file.
    :param data: data as dictionary.
    :returns: data as bytes.
    """
    try:
        if filename.endswith((".json")):
            data_as_bytes = json.dumps(data).encode("utf-8")
        elif filename.endswith((".yml", ".yaml")):
            data_as_bytes = yaml.safe_dump(data).encode("utf-8")
        else:
            raise ValueError(f"Unsupported file type: {filename}")
        return data_as_bytes
    except ValueError:
        raise
    except (TypeError, yaml.YAMLError):
        raise ValueError(f"Failed to serialize data for {filename}")


def _validate_and_convert_to_dict(filename: str, data: bytes) -> dict:
    """Validates filename based on extension and converts data into dictionary.

    :param filename: name of file.
    :param data: data as bytes.
    :returns: data as dict.
    """
    try:
        if filename.endswith((".json")):
            data_as_dict = json.loads(data)  # Throw away - decoding for validation only
        elif filename.endswith((".yml", ".yaml")):
            data_as_dict = yaml.safe_load(data)  # Throw away - decoding for validation only
        else:
            raise ValueError(f"Unsupported file type: {filename}")
        return data_as_dict
    except ValueError:
        raise
    except (json.JSONDecodeError, yaml.YAMLError):
        raise ValueError(f"Failed to decode data for {filename}")
