import json
import re
import yaml

from ficus.core.exceptions import (
    ConfigExistsError,
    ConfigDecodeError,
    ConfigNotFoundError,
    ConfigSerializeError,
    InvalidNamespaceError,
    InvalidScopeError,
    InvalidScopeIdentifierError,
    MultipleScopeIdentifiersError,
    NotEmptyError,
    PathIsDirectoryError,
    PathNotFoundError,
    UnsupportedFileTypeError,
)
from ficus.core.config import settings
from ficus.database.data_store import DataStore
from ficus.schemas.configs import ConfigData
from pathlib import Path


DEFAULT_FILES = {"default.yml", "default.yaml", "default.json"}


ScopeName = str

def _get_all_search_paths(
    data_store: DataStore,
    namespace: str,
    scope_identifiers: dict[ScopeName, str] | None = None) -> list[Path]:
    """Get all folder paths for the specified namespace and scope idenfitiers.

    Return path order is in merge priority order (highest to lowest) starting
    with defaults and followed by scopes in scope priority order.

    Scope priority is specified by the order the input `scope_identifiers` dict.
    """
    if scope_identifiers is None:
        scope_identifiers = {}
    paths = [data_store.rootdir / Path(f"defaults/{namespace}")]
    if not data_store.exists(paths[-1]):
        raise InvalidNamespaceError(f"Namespace not found in defaults: {namespace}")
    for scope, identifier in scope_identifiers.items():
        # FIXME: global settings
        if scope not in settings.scopes:
            raise InvalidScopeError(f"Scope {scope} does not exist. Valid scopes "
                                    f"are: {settings.scopes}.")
        paths.append(data_store.rootdir / Path(f"{scope}/{identifier}/{namespace}"))
        if not data_store.exists(paths[-1]):
            first_invalid_subpath = _find_first_invalid_subpath(data_store=data_store,
                                                                path=paths[-1],
                                                                is_file=False)
            error_map = \
            {
                f"{scope}": InvalidScopeError,
                f"{identifier}": InvalidScopeIdentifierError,
                f"{namespace}": InvalidNamespaceError
            }
            error_msg = f"Path does not exist: {first_invalid_subpath}"
            raise error_map.get(first_invalid_subpath.name, PathNotFoundError)(error_msg)
    return paths


def get_config(
    data_store: DataStore,
    namespace: str,
    scope_identifiers: dict[ScopeName, str] | None = None,
    filename: str | None = None,
    merge: bool = True,
) -> tuple[ConfigData, list[Path]]:
    """
    Get config file from store based on namespace and scopes.

    If filename is not given, function will search for the default config file. The default config
    files are default.yml, default.yaml, and default.json.

    If merge is true, function will merge config files found in each scope. The merge is done in
    order of scopes given by the dictionary of scope identifiers. Later configs will override
    previous configs.

    Parameters:
    -----------
        namespace: str
            The namespace for the configuration file.
        scope_identifiers: dict[ScopeName, str]
            A dictionary of scope identifier names. Scope *resolution order* is
            determined by dict order. aka: Overrides are applied from back to front.
            (i.e: for dict: `{"subject_id": "mouse_0", "hostname": "W10BRUNO"}`,
            values from the hostname: W10BRUNO override values in subject_id: mouse_0,
            which override any defaults.)
        filename: str | None
            The name of the configuration file, including extension. If None, the default config
            file will be used.
        merge: bool
            Whether to merge config files found in each scope. If false, only the config file in
            the last scope from identifier names will be returned.

    Returns:
    --------
        tuple[ConfigData, list[Path]]
            A tuple containing the configuration data and a list of paths the config was made from.
    """
    if filename is None:
        filename = "default.yml"
    config = {}
    try:
        file_override_paths = get_file_override_stack(data_store=data_store,
                                                      namespace=namespace,
                                                      scope_identifiers=scope_identifiers,
                                                      filename=filename)
    except FileNotFoundError:
        raise ConfigNotFoundError()
    if not file_override_paths:
        raise ConfigNotFoundError()
    # Iterate backwards so we can return immediately if not merging.
    for filepath in reversed(file_override_paths):
        override_config_bytes = data_store.read(filepath)
        override_config = _validate_and_convert_to_dict(filepath.suffix, override_config_bytes)
        config = _deep_update(override_config, config)
        if not merge:
            return config, [file_override_paths[-1]]
    return config, file_override_paths


def save_config(
    data_store: DataStore,
    namespace: str,
    filename: str,
    data: dict,
    scope_identifiers: dict[ScopeName, str],
    override: bool = False,
    create_if_missing: bool = True,
) -> tuple[dict, str]:
    """
    Save config file to zookeeper based on namespace, scopes, and identifier.

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
        scope_identifiers: dict[ScopeName, str]
            A dict, keyed by scope name, of identifiers per scope.
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
    if scope_identifiers and len(scope_identifiers) > 1:
        raise MultipleScopeIdentifiersError(
            f"Multiple identifier names provided: {list(scope_identifiers.keys())}. "
            "Only one is allowed."
        )

    scope = None
    identifier = None
    if scope_identifiers:
        (scope, identifier), = scope_identifiers.items()
        if scope not in settings.scopes:
            raise InvalidScopeError(f"Scope {scope} does not exist. Valid scopes "
                                    f"are: {settings.scopes}.")

    # Convert data to bytes and save to zookeeper using helper function
    data_as_bytes = _validate_and_convert_to_bytes(filename, data)
    return _save_config(
        data_store=data_store,
        namespace=namespace,
        filename=filename,
        data=data_as_bytes,
        scope=scope,
        identifier=identifier,
        override=override,
        create_if_missing=create_if_missing,
    )


def update_config(
    data_store: DataStore,
    namespace: str,
    filename: str,
    data: dict,
    scope_identifiers: dict[ScopeName, str]
):
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
        scope_identifiers: dict[ScopeName, str]
            A dict, keyed by scope name, of identifiers per scope.

    Returns:
    --------
        tuple[dict, str]
            A tuple containing the updated configuration data and the path the config was saved to.
    """
    if scope_identifiers and len(scope_identifiers) > 1:
        raise MultipleScopeIdentifiersError(
            f"Multiple identifier names provided: {list(scope_identifiers.keys())}. "
            "Only one is allowed."
        )
    scope = None
    identifier = None
    if scope_identifiers:
        (scope, identifier), = scope_identifiers.items()
        if scope not in settings.scopes:
            raise InvalidScopeError(f"Scope {scope} does not exist. Valid scopes "
                                    f"are: {settings.scopes}.")

    current_config, _ = get_config(
        data_store=data_store, namespace=namespace, filename=filename,
        scope_identifiers=scope_identifiers, merge=False
    )
    # Throw away value, only want to validate
    _validate_and_convert_to_bytes(filename=f"{filename}", data=data)
    raw_config = _deep_update(current_config, data)
    config = _validate_and_convert_to_bytes(filename, raw_config)
    return _save_config(
        data_store=data_store,
        namespace=namespace,
        filename=filename,
        data=config,
        scope=scope,
        identifier=identifier,
        override=True,
        create_if_missing=False,
    )


def delete_config(
    data_store: DataStore, namespace: str, filename: str,
    scope_identifiers: dict[ScopeName, str] | None = None
) -> str:
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
        scope_identifiers: dict[ScopeName, str]
            A dict, keyed by scope name, of identifiers per scope.

    Returns:
    --------
        str
            The path of the deleted config file.
    """
    if scope_identifiers and len(scope_identifiers) > 1:
        raise MultipleScopeIdentifiersError(
            f"Multiple identifier names provided: {list(scope_identifiers.keys())}. "
            "Only one is allowed."
        )
    scope = None
    identifier = None
    if scope_identifiers:
        (scope, identifier), = scope_identifiers.items()
        if scope not in settings.scopes:
            raise InvalidScopeError(f"Scope {scope} does not exist. Valid scopes "
                                    f"are: {settings.scopes}.")

    if scope and identifier:
        path = data_store.rootdir / f"{scope}/{identifier}/{namespace}/{filename}"
    else:
        path = data_store.rootdir / f"defaults/{namespace}/{filename}"

    try:
        data_store.delete(path)
        return str(path)
    except NotEmptyError:
        raise PathIsDirectoryError(f"Path is a directory and cannot be deleted: {path}")
    except PathNotFoundError:
        invalid_subpath = _find_first_invalid_subpath(data_store, path)
        if invalid_subpath:
            raise ConfigNotFoundError(f"Subpath '{invalid_subpath}' not found in path: {path}")
        raise ConfigNotFoundError(f"Config file not found at path: {path}")


def list_all_filenames(
    data_store: DataStore,
    namespace: str,
    scope_identifiers: dict[ScopeName, str] | None = None,
) -> list[str]:
    """For a given namespace and scope identifiers, return all matching files.
    Returns
    -------
        list[str]
            list of filenames matching namespace and scope identifiers in
            alphabetical order.
    """
    lowest_scope_path = _get_all_search_paths(data_store=data_store,
                                              namespace=namespace,
                                              scope_identifiers=scope_identifiers)[-1]
    return sorted(data_store.list_files(lowest_scope_path), key=str.lower)

def get_file_override_stack(
    data_store: DataStore,
    namespace: str,
    filename: str,
    scope_identifiers: dict[ScopeName, str] | None = None,
    must_exist_in_any_scope: bool = True,
    must_exist_in_lowest_scope: bool = True
) -> list[Path]:
    """For a given namespace, scope_identifiers, and filename, return the full
    hierarchy of files that apply to this file in reverse override order i.e:
    val[-1] overrides val[-2] which overrides ... val[-N]

    Parameters:
    -----------
        data_store: DataStore
            storage location to search.
        namespace: str
            The namespace for the configuration files.
        scope_identifiers: dict[ScopeName, str]
            A dict, keyed by scope name, of identifiers per scope to filter by.
            If None are provided, only include the default scope.
        filename: str | None
            The name of the configuration file to filter by, including extension.
    """
    # Warning: we don't check to see if multiple defaults are present.
    override_stack = []
    valid_files = DEFAULT_FILES | {filename}
    paths = _get_all_search_paths(data_store, namespace, scope_identifiers)
    # Get defaults, followed by config name in each namespace.
    for folder_path in paths:
        if not data_store.exists(folder_path):
            raise InvalidScopeIdentifierError(f"Folder does not exist: {folder_path}")
        # Sort with defaults first.
        for filename_ in sorted(data_store.list_files(folder_path),
                           key=lambda x: "" if x.lower() in DEFAULT_FILES else x.lower()):
            # Append default if it exists.
            if filename_ in valid_files:
                override_stack.append(folder_path / filename_)
    # FIXME: what do we want to happen here?
    #if must_exist_in_any_scope:
    #    found_filenames = [f.name for f in override_stack]
    #    if filename not in found_filenames:
    #        raise FileNotFoundError()
    #if must_exist_in_lowest_scope:
    #    if override_stack[-1].name != filename:
    #        raise FileNotFoundError()

    if must_exist_in_any_scope:
        found_filenames = [f.stem for f in override_stack]
        if Path(filename).stem not in found_filenames:
            raise FileNotFoundError()
    if must_exist_in_lowest_scope:
        if override_stack[-1].stem != Path(filename).stem:
            raise FileNotFoundError()
    return override_stack


def get_all_override_stacks(
    data_store: DataStore,
    namespace: str,
    scope_identifiers: dict[ScopeName, str] | None = None) -> list[list[Path]]:
    """
    Get override stacks for all files matching namespace and scope(s).

    If no scopes are given, function will only check the defaults scope.
    If multiple scopes, the path order is the order of the scope_identifiers.
    (This order is also the same as the merge order.)

    Parameters:
    -----------
        data_store: DataStore
            storage location to search.
        namespace: str
            The namespace for the configuration files.
        scope_identifiers: dict[ScopeName, str]
            A dict, keyed by scope name, of identifiers per scope to filter by.
            If None are provided, only include the default scope.

    Returns:
    --------
        list[list[Path]]
            A list of file override stacks for each file at the lowest level
            scope that matches the namespace. List order is aphabetical by filename.
    """
    file_stacks = []
    filenames = list_all_filenames(data_store, namespace, scope_identifiers)
    for filename in filenames:
        file_stacks.append(get_file_override_stack(data_store=data_store,
                                                   namespace=namespace,
                                                   scope_identifiers=scope_identifiers,
                                                   filename=filename))
    return file_stacks


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


def _get_default_config(data_store: DataStore, path: Path) -> tuple[dict, Path]:
    """
    Helper function to get default config file from zookeeper and handle errors.
    Checks all default file options (default.yml, default.yaml, default.json) and returns the first
    one it finds, in that order. The write/save function will stop from saving a default file if one
    already exists.
    """
    for defaults in DEFAULT_FILES:
        try:
            default_data = _get_config(data_store, path / f"{defaults}")
            if default_data is None:
                default_data = {}
            return default_data, path/ f"{defaults}"
        except ConfigNotFoundError:
            pass  # Ignore file not found, default could have different extension
    raise ConfigNotFoundError(f"default.[yml/yaml/json] not found at path: {path}")


def _get_config(data_store: DataStore, path: Path) -> dict:
    """
    Helper function to get config file from zookeeper and handle errors.
    Function will check each subpath incrementally and return the first subpath that failed if file
    is not found.
    """
    try:
        data = _validate_and_convert_to_dict(path, data_store.read(path))
        # Not a config!
        if not isinstance(data, dict):
            raise ConfigNotFoundError(f"File at {path} is not a valid config!")
        return data
    except PathNotFoundError:
        invalid_subpath = _find_first_invalid_subpath(data_store, path)
        if invalid_subpath:
            raise ConfigNotFoundError(f"Subpath '{invalid_subpath}' not found in path: {path}")
        raise ConfigNotFoundError(f"Config file not found at path: {path}")


def _find_first_invalid_subpath(
    data_store: DataStore,
    path: Path | str,
    is_file: bool = True
) -> Path | None:
    """
    Given a path, finds the first "directory" or zk node that does not exists.

    Returns:
    -------
        str | None
            subpath if one does not exists, or None if path is valid
    """
    path = Path(path)
    for parent in reversed(path.relative_to(data_store.rootdir).parents):
        if not data_store.exists(parent):
            return parent
    return None


def _save_config(
    data_store: DataStore,
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
            The config file identifier for the given scope.
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
        CONFIG_PATH = data_store.rootdir / f"{scope}/{identifier}/{namespace}"
    else:
        CONFIG_PATH = data_store.rootdir / f"defaults/{namespace}"
    filepath = f"{CONFIG_PATH}/{filename}"
    if not override:
        # Not overriding, check default file doesn't already exist (if saving default)
        if filename in DEFAULT_FILES:
            for df in DEFAULT_FILES:
                if data_store.path_exists(f"{CONFIG_PATH}/{df}"):
                    raise ConfigExistsError(f"Default File already exists: {CONFIG_PATH}/{df}")
        # Not overriding, check normal file doesn't already exist
        if data_store.path_exists(filepath):
            raise ConfigExistsError(f"File already exists: {filepath}")
    # Overriding, if create_if_missing is false, check file exists before overriding
    if not data_store.path_exists(filepath) and not create_if_missing:
        invalid_subpath = _find_first_invalid_subpath(data_store, filepath)
        if invalid_subpath:
            raise ConfigNotFoundError(f"Subpath '{invalid_subpath}' not found in "
                                      f"path: {filepath}")
        raise ConfigNotFoundError(f"Config file not found at path: {filepath}")
    # Overriding and create if missing
    if data_store.path_exists(filepath):
        data_store.update(filepath, data)
    else:
        data_store.create(filepath, data)
    return _validate_and_convert_to_dict(filename, data), filepath


def _validate_and_convert_to_bytes(suffix: str, data: dict) -> bytes:
    """
    Validates filename based on extension and converts data into bytes.
    Only attempts to validate/convert json and yaml files.
    """
    try:
        if suffix == ".json":
            data_as_bytes = json.dumps(data).encode("utf-8")
        elif suffix in [".yml", ".yaml"]:
            data_as_bytes = yaml.safe_dump(data).encode("utf-8")
        else:
            raise UnsupportedFileTypeError(f"Unsupported file type: {suffix}")
        return data_as_bytes
    except (TypeError, yaml.YAMLError):
        raise ConfigSerializeError(f"Failed to serialize data for {suffix}")


def _validate_and_convert_to_dict(suffix: str, data: bytes) -> dict:
    """
    Validates filename based on extension and converts data into dictionary.
    Only attempts to validate/convert json and yaml files.
    """
    try:
        if suffix == ".json":
            data_as_dict = json.loads(data)  # Throw away - decoding for validation only
        elif suffix in [".yml", ".yaml"]:
            data_as_dict = yaml.safe_load(data)  # Throw away - decoding for validation only
            if data_as_dict is None:
                # yaml.safe_load returns None for empty files, convert to empty dict
                data_as_dict = {}
        else:
            raise UnsupportedFileTypeError(f"Unsupported file type: {suffix}")
        return data_as_dict
    except (json.JSONDecodeError, yaml.YAMLError):
        raise ConfigDecodeError(f"Failed to decode data for {suffix}")
