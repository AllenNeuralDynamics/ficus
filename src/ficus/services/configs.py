import copy
import json
from loguru import logger
from ficus.utils.dict_merge import _deep_update, _deep_update_existing_destructive
import yaml

from ficus.core.exceptions import (
    ConfigExistsError,
    ConfigDecodeError,
    ConfigMutatedError,
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
from ficus.database.data_store import DataStore
from ficus.schemas.configs import ConfigData
from pathlib import Path, PurePath


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

    Raises
    -------
    InvalidScopeError
        if the scope does not exist.
    InvalidScopeIdentifierError
        if the scope identifier does not exist.
    InvalidNamespaceError
        if the namespace does not exist.
    """
    if scope_identifiers is None:
        scope_identifiers = {}
    paths = [data_store.rootdir / Path(f"defaults/{namespace}")]
    if not data_store.exists(paths[-1]):
        raise InvalidNamespaceError(f"Namespace not found in defaults: {namespace}")
    for scope, identifier in scope_identifiers.items():
        if scope not in data_store.scopes:
            raise InvalidScopeError(f"Scope {scope} does not exist. Valid scopes "
                                    f"are: {data_store.scopes}.")
        paths.append(data_store.rootdir / Path(f"{scope}/{identifier}/{namespace}"))
        if not data_store.exists(paths[-1]):
            first_invalid_subpath = _find_first_invalid_subpath(data_store=data_store,
                                                                path=paths[-1])
            error_map = \
            {
                f"{scope}": InvalidScopeError,
                f"{identifier}": InvalidScopeIdentifierError,
                f"{namespace}": InvalidNamespaceError
            }
            error_msg = f"Path does not exist: {first_invalid_subpath}"
            raise error_map.get(first_invalid_subpath.name, PathNotFoundError)(error_msg)
    return paths


def _ensure_paths(
    data_store: DataStore,
    namespace: str | None,
    scope_identifiers: dict[ScopeName, str] | None):
    """Create underlying data store structure to guarantee that namespace and
    scope identifiers exist."""
    namespace = namespace if namespace is not None else ""
    scope_identifiers = scope_identifiers if scope_identifiers is not None else {}
    # Create default namespace.
    default_namespace_path = data_store.rootdir / Path(f"defaults/{namespace}")
    if namespace and not data_store.exists(default_namespace_path):
            data_store.create(path=default_namespace_path, data=None)
            logger.debug(f"creating: {default_namespace_path}")
    for scope, identifier in scope_identifiers.items():
        # Create each scope with internal namespace.
        scope_id_path = data_store.rootdir / Path(f"{scope}/{identifier}")
        if namespace:
            scope_id_path = scope_id_path / Path(namespace)
        if not data_store.exists(scope_id_path):
            logger.debug(f"creating: {scope_id_path}")
            data_store.create(path=scope_id_path, data=None)


def _get_parts_from_path(data_store: DataStore, path: Path
) -> tuple[str, dict[ScopeName, str], str | None]:
    namespace = ""
    scope_identifier = {}
    filename = None
    subpath_from_root = data_store._sanitize(path).relative_to(data_store.rootdir)
    path_parts = list(subpath_from_root.parts)
    if path_parts[0] == "defaults":  # default scope case.
        namespace = path_parts[1]
        path_parts = path_parts[2:]
    else:  # named scope case
        scope_identifier[path_parts[0]] = path_parts[1]
        namespace = path_parts[2]
        path_parts = path_parts[3:]
    if len(path_parts):
        filename = path_parts[0]
    return namespace, scope_identifier, filename


def _ensure_single_scope(
    data_store: DataStore,
    scope_identifiers: dict[ScopeName, str] | None = None,
    validate_scope: bool = True,
)-> tuple[ScopeName | None, str | None]:
    scope, identifier = None, None
    if scope_identifiers and len(scope_identifiers) > 1:
        raise MultipleScopeIdentifiersError(
            f"Multiple identifier names provided: {list(scope_identifiers.keys())}. "
            "Only one is allowed."
        )
    if scope_identifiers:
        (scope, identifier), = scope_identifiers.items()
        if validate_scope and scope not in data_store.scopes:
            raise InvalidScopeError(f"Scope {scope} does not exist. Valid scopes "
                                    f"are: {data_store.scopes}.")
    return scope, identifier


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
    scope_identifier: dict[ScopeName, str],
    filename: str,
    data: dict,
    override: bool = False,
    create_missing_paths: bool = False
) -> tuple[dict, Path]:
    """
    Save input data to a single file in the data store based on namespace, scope,
    and identifier. If the config does not already exist, create it. Throw an
    error if the file already exists if `override=False`.

    If scope and/or identifier do not exist and `create_missing_paths=True`,
    create them.

    Identifier names are expected to correspond to a scope (auto-validates this). The function will
    also expect to be given a single identifier name since a config file can only be saved to one
    scope.

    Data will be saved to a valid yaml or json based on filename extension.

    Parameters:
    -----------
        namespace
            The namespace for the configuration file.
        filename
            The name of the configuration file, including extension.
        data
            The configuration data to save.
        scope_identifiers
            A dict, keyed by scope name, of identifiers per scope.
        override
            Whether to override the config file if it already exists (format agnostic).
            Error if file exists and `override=False`
        create_missing_path
            whether to create namespace and identifier.
    Returns:
    --------
        tuple[dict, str]
            A tuple containing the configuration data and the path the config was saved to.
    """
    if create_missing_paths:
        _ensure_paths(data_store=data_store, namespace=namespace,
                      scope_identifiers=scope_identifier)
    paths = _get_all_search_paths(data_store=data_store, namespace=namespace,
                                  scope_identifiers=scope_identifier)
    # Should be at most default scope path and scoped path.
    if len(paths) > 2:
        raise MultipleScopeIdentifiersError()
    filepath = paths[-1] / filename
    files_in_scope = list_all_filenames(data_store=data_store, namespace=namespace,
                                        scope_identifiers=scope_identifier)
    # override and override_default need to check all file extensions.
    file_stems_in_scope = [n.split(".")[0] for n in files_in_scope]
    filestem = Path(filename).stem
    if filestem in file_stems_in_scope and not override:
        raise ConfigExistsError(f"Cannot override config: {filename} in {filepath} "
                                "without override=True")
    data_as_bytes = _validate_and_convert_to_bytes(Path(filename).suffix, data)
    # Overriding and create if missing
    if data_store.exists(filepath):
        data_store.update(filepath, data_as_bytes, force=True)
    else:
        data_store.create(filepath, data_as_bytes)
    # If extension changed, delete the previous format.
    files_in_scope = list_all_filenames(data_store=data_store, namespace=namespace,
                                        scope_identifiers=scope_identifier)
    files_in_scope.remove(filename)
    cfg_in_different_format = [f for f in files_in_scope if f.startswith(filestem)]
    for cfg in cfg_in_different_format:  # should only be one other.
        data_store.delete(paths[-1] / cfg)

    return data, filepath


def save_config_deep(
    data_store: DataStore,
    namespace: str,
    scope_identifiers: dict[ScopeName, str],
    filename: str,
    data: dict,
    override_defaults: bool = False,
    append_new_fields_to_last_scope: bool = False,
) -> dict:
    """Deep save config file by walking up the override hierarchy specified in
    scope_identifiers and saving fields back to the location where they were
    inserted.

    Parameters
    ----------
    namespace:
        the config namespace.
    filename:
        the config filename including extension.
    scope_identifiers:
        dict of scope identifiers sorted in lowest-override-priority to
        highest-override-priority.
    override_defaults:
        If True allow writing to the defaults config of any scope.
        If False, put all fields that would be edited into the default file into
        a config named `filename` at the same scope. Create if missing.
    append_new_fields_to_last_scope:
        if new fields are created, append them at the lowest level scope.
        Error if new fields are created and this flag is set to False.
    """
    override_stack = get_file_override_stack(data_store=data_store,
                                              namespace=namespace,
                                              scope_identifiers=scope_identifiers,
                                              filename=filename)
    # Cache new config values before writing to each file.
    new_cfg_data: dict[Path, dict] = {}
    # Walk up the override stack and save new field values to the respective
    # place they came from. Do this locally first to check if we have leftover data.
    data_cpy = copy.deepcopy(data)
    for filepath in reversed(override_stack):
        old_level_cfg = _validate_and_convert_to_dict(filepath.suffix, data_store.read(filepath))
        level_cfg = copy.deepcopy(old_level_cfg)
        _deep_update_existing_destructive(level_cfg, data_cpy)
        # Nothing to save back if nothing actually changed.
        if old_level_cfg == level_cfg:
            continue
        # IF the data came from default.*, get a local copy of default.*,
        # save to filename at the same scope.
        if filepath.stem.lower() == "default" and not override_defaults:
            filepath = filepath.parent / f"{filename}"
        # Respect override hierarchy if filename already exists at the scope that
        # defaults would go.
        if filepath in new_cfg_data:
            priority_cfg = new_cfg_data[filepath]
            level_cfg.update(priority_cfg)
        # Track new config to be written back in batch after-the-fact.
        new_cfg_data[filepath] = level_cfg
    # Do the writes in batch after checking if extra fields exist.
    # Put any new fields at the lowest level scope.
    if data_cpy:
        if append_new_fields_to_last_scope:
            data_as_bytes = _validate_and_convert_to_bytes(override_stack[-1].suffix, data_cpy)
            data_store.update(override_stack[-1], data_as_bytes)
        else:
            raise ConfigMutatedError("Config to be saved has additional fields not "
                                     "previously found in the original config override "
                                     f"stack. New fields: {data_cpy}")

    for filepath, new_cfg_data in new_cfg_data.items():
        ns, scope_id, filename = _get_parts_from_path(data_store=data_store, path=filepath)
        save_config(data_store=data_store, namespace=ns, scope_identifier=scope_id,
                    filename=filename, data=new_cfg_data, override=True)
    return data_cpy


def update_config(
    data_store: DataStore,
    namespace: str,
    filename: str,
    data: dict,
    scope_identifiers: dict[ScopeName, str]
):
    """
    Update config file based on namespace, scope, and identifier.

    This function will get the existing config and merge it with the data given. Afterwards it will
    override the existing config file (thus having same behavior/validations as the save and get functions)

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
    # FIXME: this is basically a save where the config must already exist.

    filepath = PurePath(filename) # convert for suffix
    scope, identifier = _ensure_single_scope(data_store, scope_identifiers)
    current_config, _ = get_config(
        data_store=data_store, namespace=namespace, filename=filename,
        scope_identifiers=scope_identifiers, merge=False
    )
    # Throw away value, only want to validate
    _validate_and_convert_to_bytes(filepath.suffix, data=data)
    raw_config = _deep_update(current_config, data)
    return save_config(data_store=data_store,
                       namespace=namespace,
                       filename=filename,
                       data=raw_config,
                       scope_identifier=scope_identifiers,
                       override=True,
                       create_missing_paths=False
                       )


def delete_config(
    data_store: DataStore, namespace: str, filename: str,
    scope_identifiers: dict[ScopeName, str] | None = None
) -> str:
    """
    Delete config file based on namespace, scope, and identifier.

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

    paths = _get_all_search_paths(data_store=data_store, namespace=namespace,
                                  scope_identifiers=scope_identifiers)
    # Should be at most default scope path and scoped path.
    if len(paths) > 2:
        raise MultipleScopeIdentifiersError()
    path = paths[-1] / filename
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
    # Will also validate: namespace, scope, scope identifier.
    paths = _get_all_search_paths(data_store, namespace, scope_identifiers)
    # Get defaults, followed by config name in each namespace.
    for folder_path in paths:
        # Sort with defaults first.
        for filename_ in sorted(data_store.list_files(folder_path),
                           key=lambda x: "" if x.lower() in DEFAULT_FILES else x.lower()):
            # Append default if it exists.
            if filename_ in valid_files:
                override_stack.append(folder_path / filename_)
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

def _find_first_invalid_subpath(
    data_store: DataStore,
    path: Path | str,
) -> Path | None:
    """
    Given a path, finds the first "directory" or zk node that does not exists.

    Returns:
    -------
        str | None
            subpath if one does not exists, or None if path is valid
    """
    path = Path(path)
    try:
        # might raise ValueError if path is not relative to data_store.rootdir
        subpath_from_root = path.relative_to(data_store.rootdir)
        for parent in reversed(subpath_from_root.parents):
            if not data_store.exists(parent):
                return data_store.rootdir / parent  # reattach root
    except ValueError:
        return path.parents[-1]
    return None


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
