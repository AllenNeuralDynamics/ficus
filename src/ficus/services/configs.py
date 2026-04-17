import json
import yaml

from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError, NotEmptyError

from ficus.core.exceptions import (
    ConfigExistsError,
    ConfigDecodeError,
    ConfigNotFoundError,
    ConfigSerializeError,
    PathIsDirectoryError,
    UnsupportedFileTypeError,
)
from ficus.core.config import settings
from ficus.crud.zookeeper import get_node, add_node, delete_node
from ficus.database.zookeeper import get_zk_client
from ficus.schemas.configs import ConfigData


DEFAULTS_PATH_PREFIX = f"/{settings.zk_root_node}/defaults"
COMPUTERS_PATH_PREFIX = f"/{settings.zk_root_node}/computers"
DEFAULT_FILES = ["default.yml", "default.yaml", "default.json"]


def get_config(namespace: str, filename: str | None = None, hostname: str | None = None) -> tuple[ConfigData, list]:
    """Get configs from zookeeper. Merges defaults and partial config override for specific computers.

    :param namespace: namespace to search for file (in default and computers/<hostname>).
    :param filename: name of the file.
    :param hostname: hostname to search for a partial config override.
    :return: config data and list denoting paths of the partial files used to create the config data
    :notes: requires file to exist in defaults before grabbing computers override with hostname.
    """
    DEFAULT_PATH = f"{DEFAULTS_PATH_PREFIX}/{namespace}"
    COMPUTER_PATH = f"{COMPUTERS_PATH_PREFIX}/{hostname}/{namespace}"

    valid_paths = []

    with get_zk_client() as client:

        def get_data_and_append_path(path: str, is_default: bool = False, ignore_error: bool = False):
            try:
                if is_default:
                    data, data_path = _get_default_config(client, path)
                    valid_paths.append(data_path)
                else:
                    data = _get_config(client, path)
                    valid_paths.append(path)
                return data
            except ConfigNotFoundError as e:
                if ignore_error:
                    return {}
                else:
                    raise e

        config: dict = {}

        if not filename and not hostname:
            # default/defaults (required)
            config = _deep_update(config, get_data_and_append_path(path=DEFAULT_PATH, is_default=True))
        if not filename and hostname:
            # default/defaults (required)
            config = _deep_update(config, get_data_and_append_path(path=DEFAULT_PATH, is_default=True))
            # computer/hostname/default (required)
            config = _deep_update(config, get_data_and_append_path(path=f"{COMPUTER_PATH}", is_default=True))
        elif filename and not hostname:
            # default/defaults (optional)
            config = _deep_update(
                config, get_data_and_append_path(path=DEFAULT_PATH, is_default=True, ignore_error=True)
            )
            # default/filename (required)
            config = _deep_update(config, get_data_and_append_path(path=f"{DEFAULT_PATH}/{filename}"))
        elif filename and hostname:
            # default/defaults (optional)
            config = _deep_update(
                config, get_data_and_append_path(path=DEFAULT_PATH, is_default=True, ignore_error=True)
            )
            # default/filename (required)
            config = _deep_update(config, get_data_and_append_path(path=f"{DEFAULT_PATH}/{filename}"))
            # computer/hostname/default (optional)
            config = _deep_update(
                config, get_data_and_append_path(path=f"{COMPUTER_PATH}", is_default=True, ignore_error=True)
            )
            # computer/hostname/filename (required)
            config = _deep_update(config, get_data_and_append_path(path=f"{COMPUTER_PATH}/{filename}"))

    return config, valid_paths


def get_config_no_merge(
    namespace: str, filename: str | None = None, hostname: str | None = None
) -> tuple[ConfigData, str]:
    """Get config from zookeeper without any merging

    :param namespace: namespace to search for file (in default and computers/<hostname>).
    :param filename: name of the file.
    :param hostname: hostname to search for a partial config override.
    :return: config data and path of the config file
    """
    if hostname:
        PATH = f"{COMPUTERS_PATH_PREFIX}/{hostname}/{namespace}"
    else:
        PATH = f"{DEFAULTS_PATH_PREFIX}/{namespace}"

    with get_zk_client() as client:
        if filename:
            config_path = f"{PATH}/{filename}"
            config_data = _get_config(client, config_path)
        else:
            config_data, config_path = _get_default_config(client, PATH)
        return config_data, config_path


def save_config_obj(
    namespace: str,
    filename: str,
    data: dict,
    hostname: str | None = None,
    override: bool = False,
    create_if_missing: bool = True,
) -> tuple[dict, str]:
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
    return _save_config(
        namespace=namespace,
        filename=filename,
        data=data_as_bytes,
        hostname=hostname,
        override=override,
        create_if_missing=create_if_missing,
    )


def save_config_file(
    namespace: str,
    filename: str,
    data: bytes,
    hostname: str | None = None,
    override: bool = False,
    create_if_missing: bool = True,
) -> tuple[dict, str]:
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
    return _save_config(
        namespace=namespace,
        filename=filename,
        data=data,
        hostname=hostname,
        override=override,
        create_if_missing=create_if_missing,
    )


def update_config_object(namespace: str, filename: str, data: dict, hostname: str | None = None) -> tuple[dict, str]:
    """Update config file in zookeeper with new data (dictionary)

    :param namespace: namespace to save file to.
    :param filename: name of the file.
    :param hostname: hostname to save file to (indicates config override).
    :param data: config data as python dictionary
    :returns: path where file was updated.
    """
    current_config, _ = get_config_no_merge(namespace=namespace, filename=filename, hostname=hostname)
    _validate_and_convert_to_bytes(filename=f"{filename}", data=data)  # Throw away value, only want to validate
    raw_config = _deep_update(current_config, data)
    config = _validate_and_convert_to_bytes(filename, raw_config)
    return _save_config(
        namespace=namespace, filename=filename, data=config, hostname=hostname, override=True, create_if_missing=False
    )


def update_config_file(
    namespace: str, filename: str, partial_filename: str, data: bytes, hostname: str | None = None
) -> tuple[dict, str]:
    """Update config file in zookeeper with new data (bytes). Due to validation, if the file is a yaml file, it removes
    the comments from the file and reorders the field alphabetically.

    :param namespace: namespace to save file to.
    :param filename: name of the file.
    :param hostname: hostname to save file to (indicates config override).
    :param data: config data as bytes
    :returns: path where file was updated.
    """
    current_config, _ = get_config_no_merge(namespace=namespace, filename=filename, hostname=hostname)
    new_config = _validate_and_convert_to_dict(partial_filename, data)
    raw_config = _deep_update(current_config, new_config)
    config = _validate_and_convert_to_bytes(filename, raw_config)
    return _save_config(
        namespace=namespace, filename=filename, data=config, hostname=hostname, override=True, create_if_missing=False
    )


def delete_config(namespace: str, filename: str, hostname: str | None = None) -> str | list[str]:
    """Delete config file from zookeeper. Deletes from defaults/ OR computers/<hostname> if hostname is given.

    :param namespace: namespace to save file to.
    :param filename: name of the file.
    :param hostname: hostname to save file to (indicates config override).
    :returns: path where file was deleted.
    """
    if hostname:
        path = f"{COMPUTERS_PATH_PREFIX}/{hostname}/{namespace}/{filename}"
    else:
        path = f"{DEFAULTS_PATH_PREFIX}/{namespace}/{filename}"
    with get_zk_client() as client:
        try:
            delete_node(client, path)
            return path
        except NotEmptyError:
            raise PathIsDirectoryError(f"Path is a directory and cannot be deleted: {path}")
        except NoNodeError:
            invalid_subpath = _find_first_invalid_subpath(client, path)
            if invalid_subpath:
                raise ConfigNotFoundError(f"Subpath '{invalid_subpath}' not found in path: {path}")
            raise ConfigNotFoundError(f"Config file not found at path: {path}")


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


def get_all_files(namespace: str, hostname: str | None = None) -> list[str]:
    """Get all files under a specific namespace. If a specific hostname isn't provided, it returns all files under all
    hostnames with the specified namespace.

    :param namespace: namespace to search get all files.
    :param hostname: if given, search only in this hostname for files under given namespace.
    :returns: list of files within namespace/hostname path.
    """
    all_files = []
    with get_zk_client() as client:

        def collect_files(subpath: str):
            if client.exists(subpath):
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


def _deep_update(mapping: dict, *updating_mappings: dict) -> dict:
    """Merge two dictionaries together, with values from the updating_mapping taking precedence over the mapping.
    Will deeply merge nested dictionaries together.
    If types mismatch between mapping and updating_mapping, the value from updating_mapping will override.

    :param mapping: main dictionary to merge into
    :param updating_mappings: dictionary with overrides
    :returns: merged configuration
    """
    updated_mapping = mapping.copy()
    for updating_mapping in updating_mappings:
        for k, v in updating_mapping.items():
            if k in updated_mapping and isinstance(updated_mapping[k], dict) and isinstance(v, dict):
                updated_mapping[k] = _deep_update(updated_mapping[k], v)
            else:
                updated_mapping[k] = v
    return updated_mapping


def _get_default_config(client: KazooClient, path: str) -> tuple[dict, str]:
    """Helper function to get default config file from zookeeper.
    Checks all default file options (default.yml, default.yaml, default.json) and returns the first one it finds.

    :param path: path search for defaults file (without default.yml/json extension)
    :returns: config data as dict and path of the config file (with default file with correct extension)
    """
    for defaults in DEFAULT_FILES:
        try:
            default_data = _get_config(client, f"{path}/{defaults}")
            if default_data is None:
                default_data = {}
            return default_data, f"{path}/{defaults}"
        except ConfigNotFoundError:
            pass  # Ignore file not found, default could have different extension
    raise ConfigNotFoundError(f"Default file not found at path: {path}/default.[yml/yaml/json]")


def _get_config(client: KazooClient, path: str) -> dict:
    """Helper function to get config file from zookeeper and handle errors.
    Function will check each subpath incrementally and return the first subpath that failed if file is not found.

    :param client: zookeeper client to use for getting config.
    :param path: path to get config file from.
    :returns: config data as dict
    """
    try:
        data, _ = get_node(client, path)
        return data
    except NoNodeError:
        invalid_subpath = _find_first_invalid_subpath(client, path)
        if invalid_subpath:
            raise ConfigNotFoundError(f"Subpath '{invalid_subpath}' not found in path: {path}")
        raise ConfigNotFoundError(f"Config file not found at path: {path}")


def _find_first_invalid_subpath(client: KazooClient, path: str, is_file: bool = True) -> str | None:
    subpaths = path.split("/")
    for i in range(1, len(subpaths) + (-1 if is_file else 0)):
        subpath = "/".join(subpaths[: i + 1])
        if not client.exists(subpath):
            return subpath
    return None


def _save_config(
    namespace: str,
    filename: str,
    data: bytes,
    hostname: str | None = None,
    override: bool = False,
    create_if_missing: bool = True,
) -> tuple[dict, str]:
    """Helper function to save config file (as bytes, what zookeeper expects).

    :param namespace: namespace to save file to.
    :param filename: name of the file.
    :param data: config data as bytes
    :param hostname: hostname to save file to.
    :param override: if true and file exists, overwrite the file.
    :returns: data as dict and path where file was saved.
    """
    # This function assumes that data has already been validated
    if hostname:
        CONFIG_PATH = f"{COMPUTERS_PATH_PREFIX}/{hostname}/{namespace}"
    else:
        CONFIG_PATH = f"{DEFAULTS_PATH_PREFIX}/{namespace}"

    with get_zk_client() as client:
        if not override:
            # Not overriding, check default file doesn't already exist (if saving default)
            if filename in DEFAULT_FILES:
                for df in DEFAULT_FILES:
                    if client.exists(f"{CONFIG_PATH}/{df}"):
                        raise ConfigExistsError(f"Default File already exists: {CONFIG_PATH}/{df}")

            # Not overriding, check normal file doesn't already exist
            if client.exists(f"{CONFIG_PATH}/{filename}"):
                raise ConfigExistsError(f"File already exists: {CONFIG_PATH}/{filename}")

        # Overriding, if create_if_missing is false, check file exists before overriding
        if not client.exists(f"{CONFIG_PATH}/{filename}") and not create_if_missing:
            path = f"{CONFIG_PATH}/{filename}"
            invalid_subpath = _find_first_invalid_subpath(client, path)
            if invalid_subpath:
                raise ConfigNotFoundError(f"Subpath '{invalid_subpath}' not found in path: {path}")
            raise ConfigNotFoundError(f"Config file not found at path: {path}")

        # Overriding & creating if missing
        add_node(client, f"{CONFIG_PATH}/{filename}", data)

    return _validate_and_convert_to_dict(filename, data), f"{CONFIG_PATH}/{filename}"


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
            raise UnsupportedFileTypeError(f"Unsupported file type: {filename}")
        return data_as_bytes
    except (TypeError, yaml.YAMLError):
        raise ConfigSerializeError(f"Failed to serialize data for {filename}")


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
            if data_as_dict is None:
                data_as_dict = {}  # yaml.safe_load returns None for empty files, convert to empty dict
        else:
            raise UnsupportedFileTypeError(f"Unsupported file type: {filename}")
        return data_as_dict
    except (json.JSONDecodeError, yaml.YAMLError):
        raise ConfigDecodeError(f"Failed to decode data for {filename}")
