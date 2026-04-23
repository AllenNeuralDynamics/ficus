import json
import re
import yaml

from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError, NotEmptyError

from ficus.core.exceptions import (
    ConfigExistsError,
    ConfigDecodeError,
    ConfigNotFoundError,
    ConfigSerializeError,
    InvalidScopeIdentifierError,
    MultipleScopeIdentifiersError,
    PathIsDirectoryError,
    UnsupportedFileTypeError,
)
from ficus.core.config import settings
from ficus.crud.zookeeper import get_node, add_node, delete_node
from ficus.database.zookeeper import get_zk_client
from ficus.schemas.configs import ConfigData


DEFAULT_FILES = ["default.yml", "default.yaml", "default.json"]
PATH_PREFIX = f"/{settings.zk_root_node}"


def get_config(
    namespace: str,
    identifier_names: dict[str, str] = {},
    filename: str | None = None,
    merge: bool = True,
) -> tuple[ConfigData, list[str]]:
    """
    Get config file from zookeeper based on namespace, scope, and identifier.

    If filename is not given, function will search for the default config file. The default config
    files are default.yml, default.yaml, and default.json.

    If merge is true, function will merge config files found in each scope. The merge is done in
    order of scopes given by the dictionary of identifier names. Later configs will override
    previous configs.

    Parameters:
    -----------
        namespace: str
            The namespace for the configuration file.
        identifier_names: dict[str, str]
            A dictionary of identifier names for different scopes.
        filename: str | None
            The name of the configuration file, including extension. If None, the default config
            file will be used.
        merge: bool
            Whether to merge config files found in each scope. If false, only the config file in
            the last scope from identifier names will be returned.

    Returns:
    --------
        tuple[ConfigData, list[str]]
            A tuple containing the configuration data and a list of paths the config was made from.
    """
    # Order of identifier_names determines order of scopes to merge
    scopes = _get_scope_from_identifier_names(identifier_names)
    paths = [f"/{settings.zk_root_node}/defaults/{namespace}"]
    for scope, identifier in scopes.items():
        paths.append(f"/{settings.zk_root_node}/{scope}/{identifier}/{namespace}")

    valid_paths = []
    config: dict = {}

    with get_zk_client() as client:

        def get_data_and_append_path(
            path: str, is_default: bool = False, ignore_error: bool = False
        ) -> dict:
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

        if merge:
            for path in paths:
                if filename:
                    config = _deep_update(
                        config, get_data_and_append_path(path, is_default=True, ignore_error=True)
                    )
                    config = _deep_update(config, get_data_and_append_path(f"{path}/{filename}"))
                else:
                    config = _deep_update(config, get_data_and_append_path(path, is_default=True))
        else:
            config = (
                get_data_and_append_path(f"{paths[-1]}/{filename}")
                if filename
                else get_data_and_append_path(paths[-1], is_default=True)
            )

    return config, valid_paths


def save_config(
    namespace: str,
    filename: str,
    data: dict,
    identifier_names: dict[str, str],
    override: bool = False,
    create_if_missing: bool = True,
) -> tuple[dict, str]:
    """
    Save config file to zookeeper based on namespace, scope, and identifier.

    Identifier names are expected to correspond to a scope (auto-validates this). The function will
    also expect to be given a single identifier name since a config file can only be saved to one
    scope.

    Data will also be expected to be a valid yaml or json based on filename extension, and will be
    validated and converted to bytes before saving to zookeeper.

    Parameters:
    -----------
        namespace: str
            The namespace for the configuration file.
        filename: str
            The name of the configuration file, including extension.
        data: dict
            The configuration data to save.
        identifier_names: dict[str, str]
            A dictionary of identifier names for different scopes.
        override: bool
            Whether to override the config file if it already exists. If false and file exists,
            error will be raised.
        create_if_missing: bool
            Whether to create the config file if it does not exist when overriding. If false and
            file does not exist when overriding, error will be raised.
    Returns:
    --------
        tuple[dict, str]
            A tuple containing the configuration data and the path the config was saved to.
    """
    if identifier_names and len(identifier_names) > 1:
        raise MultipleScopeIdentifiersError(
            f"Multiple identifier names provided: {(identifier_names.keys())}. Only one is allowed."
        )

    scopes = _get_scope_from_identifier_names(identifier_names)

    scope = None if not identifier_names else list(scopes.keys())[0]
    identifier = None if not identifier_names or not scope else scopes[scope]

    # Convert data to bytes and save to zookeeper using helper function
    data_as_bytes = _validate_and_convert_to_bytes(filename, data)
    return _save_config(
        namespace=namespace,
        filename=filename,
        data=data_as_bytes,
        scope=scope,
        identifier=identifier,
        override=override,
        create_if_missing=create_if_missing,
    )


def update_config(namespace: str, filename: str, data: dict, identifier_names: dict[str, str]):
    """
    Update config file in zookeeper based on namespace, scope, and identifier.

    This function will get the existing config and merge it with the data given. Afterwards it will
    treat this merged config as a new config and save it to zookeeper, overriding the existing
    config file (thus having same behavior/validations as the save and get functions)

    Parameters:
    -----------
        namespace: str
            The namespace for the configuration file.
        filename: str
            The name of the configuration file, including extension.
        data: dict
            The configuration data to update.
        identifier_names: dict[str, str]
            A dictionary of identifier names for different scopes.

    Returns:
    --------
        tuple[dict, str]
            A tuple containing the updated configuration data and the path the config was saved to.
    """
    if len(identifier_names) > 1:
        raise MultipleScopeIdentifiersError(
            f"Multiple identifier names provided: {(identifier_names.keys())}. Only one is allowed."
        )

    scopes = _get_scope_from_identifier_names(identifier_names)

    scope = None if not identifier_names else list(scopes.keys())[0]
    identifier = None if not identifier_names or not scope else scopes[scope]

    current_config, _ = get_config(
        namespace=namespace, filename=filename, identifier_names=identifier_names, merge=False
    )
    _validate_and_convert_to_bytes(
        filename=f"{filename}", data=data
    )  # Throw away value, only want to validate
    raw_config = _deep_update(current_config, data)
    config = _validate_and_convert_to_bytes(filename, raw_config)
    return _save_config(
        namespace=namespace,
        filename=filename,
        data=config,
        scope=scope,
        identifier=identifier,
        override=True,
        create_if_missing=False,
    )


def delete_config(namespace: str, filename: str, identifier_names: dict[str, str]) -> str:
    """
    Delete config file in zookeeper based on namespace, scope, and identifier.

    Identifier names are expected to correspond to a scope (auto-validates this). The function will
    also expect to be given a single identifier name since a config file can only be saved to one
    scope.

    Parameters:
    -----------
        namespace: str
            The namespace for the configuration file.
        filename: str
            The name of the configuration file, including extension.
        identifier_names: dict[str, str]
            A dictionary of identifier names for different scopes.

    Returns:
    --------
        str
            The path of the deleted config file.
    """
    if len(identifier_names) > 1:
        raise MultipleScopeIdentifiersError(
            f"Multiple identifier names provided: {(identifier_names.keys())}. Only one is allowed."
        )

    scopes = _get_scope_from_identifier_names(identifier_names)

    scope = None if not identifier_names else list(scopes.keys())[0]
    identifier = None if not identifier_names or not scope else scopes[scope]

    if scope and identifier:
        path = f"{PATH_PREFIX}/{scope}/{identifier}/{namespace}/{filename}"
    else:
        path = f"{PATH_PREFIX}/defaults/{namespace}/{filename}"

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


def get_all_files(
    namespace: str, identifier_names: dict[str, str], filename: str | None = None
) -> list[str]:
    """
    Get all config files in zookeeper based on namespace, scope, and identifier.

    If filename is given, function will filter files by the filename (case-insensitive).
    If no identifiers are given, function will only check the defaults scope.

    Parameters:
    -----------
        namespace: str
            The namespace for the configuration files.
        identifier_names: dict[str, str]
            A dictionary of identifier names for different scopes.
        filename: str | None
            The name of the configuration file to filter by, including extension. If None, all files are returned.

    Returns:
    --------
        list[str]
            A list of full paths of the config files.
    """
    scopes = _get_scope_from_identifier_names(identifier_names)

    paths = [f"/{settings.zk_root_node}/defaults/{namespace}"]
    for scope, identifier in scopes.items():
        paths.append(f"/{settings.zk_root_node}/{scope}/{identifier}/{namespace}")

    all_files = []
    with get_zk_client() as client:

        def collect_files(subpath: str):
            if client.exists(subpath):
                for file in get_node(client, subpath)[1]:
                    if filename is None or re.search(filename, file, re.IGNORECASE):
                        all_files.append(f"{subpath}/{file}")

        for path in paths:
            collect_files(path)

    return all_files


################################################################################
#
#   Utility
#
################################################################################


def _deep_update(mapping: dict, *updating_mappings: dict) -> dict:
    """
    Merge two dictionaries together, with values from the updating_mapping taking precedence over
    mapping. Merges deeply (nested dictionaries will also merge) and handles overriding types.

    Parameters:
    -----------
        mapping: dict
            The main dictionary to merge into.
        updating_mappings: dict
            Dictionary with overrides to merge into the main dictionary.
    Returns:
    --------
        dict
            The merged dictionary.
    """
    updated_mapping = mapping.copy()
    for updating_mapping in updating_mappings:
        for k, v in updating_mapping.items():
            if (
                k in updated_mapping
                and isinstance(updated_mapping[k], dict)
                and isinstance(v, dict)
            ):
                updated_mapping[k] = _deep_update(updated_mapping[k], v)
            else:
                updated_mapping[k] = v
    return updated_mapping


def _get_default_config(client: KazooClient, path: str) -> tuple[dict, str]:
    """
    Helper function to get default config file from zookeeper and handle errors.
    Checks all default file options (default.yml, default.yaml, default.json) and returns the first
    one it finds, in that order. The write/save function will stop from saving a default file if one
    already exists.
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
    """
    Helper function to get config file from zookeeper and handle errors.
    Function will check each subpath incrementally and return the first subpath that failed if file is not found.
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
    """
    Given a path, finds the first "directory" or zk node that does not exists.

    Returns:
    -------
        str | None
            subpath if one does not exists, or None if path is valid
    """
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
    scope: str | None = None,
    identifier: str | None = None,
    override: bool = False,
    create_if_missing: bool = True,
) -> tuple[dict, str]:
    """Helper function to save config file to zookeeper.

    Throws an error if a default file (default.[yml/yaml/json]) already exists and trying to save a
    new default file, unless overriding.

    Parameters:
    -----------
        namespace: str
            The namespace for the configuration file.
        filename: str
            The name of the configuration file.
        data: bytes
            The data to be saved in the configuration file.
        scope: str | None, optional
            The scope of the configuration file.
        identifier: str | None, optional
            The identifier for the configuration file.
        override: bool, optional
            Whether to override the existing configuration file.
        create_if_missing: bool, optional
            Whether to create the configuration file if it does not exist.

    Returns:
    --------
        tuple[dict, str]
            A tuple containing the configuration data and the path the config was saved to.
    """

    if scope and identifier:
        CONFIG_PATH = f"{PATH_PREFIX}/{scope}/{identifier}/{namespace}"
    else:
        CONFIG_PATH = f"{PATH_PREFIX}/defaults/{namespace}"
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
    """
    Validates filename based on extension and converts data into bytes.
    Only attempts to validate/convert json and yaml files.
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
    """
    Validates filename based on extension and converts data into dictionary.
    Only attempts to validate/convert json and yaml files.
    """
    try:
        if filename.endswith((".json")):
            data_as_dict = json.loads(data)  # Throw away - decoding for validation only
        elif filename.endswith((".yml", ".yaml")):
            data_as_dict = yaml.safe_load(data)  # Throw away - decoding for validation only
            if data_as_dict is None:
                # yaml.safe_load returns None for empty files, convert to empty dict
                data_as_dict = {}
        else:
            raise UnsupportedFileTypeError(f"Unsupported file type: {filename}")
        return data_as_dict
    except (json.JSONDecodeError, yaml.YAMLError):
        raise ConfigDecodeError(f"Failed to decode data for {filename}")


def _get_scope_from_identifier_names(identifier_names: dict[str, str]) -> dict[str, str]:
    """
    Given a dictionary of identifier names, validates that they correspond to actual scopes and
    returns a dictionary mapping scope names to identifier values.

    The scope to identifier name mapping is determined by the settings file (ficus_setup.json)

    Parameters:
    -----------
    identifier_names: dict[str, str]
        A dictionary of identifier names for different scopes, where keys are scope identifier
        names and values are the corresponding identifier values.

    Returns:
    --------
        dict[str, str]
            A dictionary mapping scope names to identifier values.
    """
    id_name_to_scope_name_mapping = {scope.identifier_name: scope for scope in settings.scopes}
    scopes = {}
    for id_name in identifier_names:
        # Validates id_name maps to a scope
        if id_name not in id_name_to_scope_name_mapping:
            raise InvalidScopeIdentifierError(
                f"Invalid scope identifier name: {id_name}. "
                f"Valid options are: {list(id_name_to_scope_name_mapping.keys())}"
            )
        scope = id_name_to_scope_name_mapping[id_name]
        scopes[scope.name] = identifier_names[id_name]  # identifier value
    return scopes
