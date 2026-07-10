import copy
import json
from typing import Literal, Optional
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

DEFAULT_MODE = "default"
DEFAULT_FILES = {"default.yml", "default.yaml", "default.json"}
VALID_EXTENSIONS_TYPE = Literal[".yaml", ".yml", ".json"]
VALID_EXTENSIONS = {".yaml", ".yml", ".json"}
DEFAULT_SUFFIX = ".yml"


ScopeName = str


def _get_all_search_paths(
    data_store: DataStore,
    namespace: str | None = None,
    scope_identifiers: dict[ScopeName, str] | None = None) -> list[Path]:
    """Get all folder paths for the specified namespace and scope idenfitiers.

    Return path order is in merge priority order (highest to lowest) starting
    with defaults and followed by scopes in scope priority order.

    Scope priority is specified by the order the input `scope_identifiers` dict.
    """
    if scope_identifiers is None:
        scope_identifiers = {}
    paths = []
    if namespace is not None:
        paths.append(data_store.rootdir / Path(f"defaults/{namespace}"))
    for scope, identifier in scope_identifiers.items():
        paths.append(data_store.rootdir / Path(f"{scope}/{identifier}/{namespace}"))
    return paths


def _ensure_paths(
    data_store: DataStore,
    # namespace: str | None,
    # scope_identifiers: dict[ScopeName, str] | None,
    paths: list[Path],
    create_missing_namespace: bool = False,
    scope_ids_must_exist: set[ScopeName] | None = None,
    create_missing_scope_id: bool = False,
    create_missing_scope: bool = False,
):
    """Create underlying data store structure to guarantee that namespace and
    scope identifiers exist.
    
    Raises
    ------
    InvalidNamespaceError
        if the namespace does not exist and create_missing_namespace is False.
    InvalidScopeError
        if a scope does not exist and create_missing_scope is False.
    InvalidScopeIdentifierError
        if a scope identifier does not exist and create_missing_scope_id is False.
    """
    ensured_paths = copy.deepcopy(paths)
    for path in paths:
        namespace, scope_identifier, filename = _get_parts_from_path(data_store, path)
        if not scope_identifier: # in the default scope
            if namespace and not data_store.exists(path):
                if create_missing_namespace:
                    data_store.create(path=path, data=None)
                    logger.debug(f"creating: {path}")
                else:
                    raise InvalidNamespaceError(f"Namespace not found in defaults: {namespace}")

        else:
            scope, identifier = _validate_single_scope(scope_identifier)
            # Validate that scope exists in the datastore
            data_store.validate_scopes(scopes={scope},
                                        create_missing=create_missing_scope)

            if not data_store.exists(path):
                if create_missing_scope_id:
                    logger.debug(f"creating: {path}")
                    data_store.create(path=path, data=None)
                elif scope_ids_must_exist and scope in scope_ids_must_exist:
                    raise InvalidScopeIdentifierError(f"Scope identifier not found: {scope}/{identifier}")
                else:
                    # if it doesn't exist and it's okay not to, just remove it from paths
                    ensured_paths.remove(path)

    return ensured_paths


def _get_parts_from_path(data_store: DataStore, path: Path
) -> tuple[str, dict[ScopeName, str], str | None]:
    """Given a path, parse it for namespace, scope identifier, filename"""
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
    if len(path_parts): # path_parts has been modified to remove everything except filename
        filename = path_parts[0]
    return namespace, scope_identifier, filename


def _validate_single_scope(
    scope_identifiers: dict[ScopeName, str] | None = None,
)-> tuple[ScopeName | None, str | None]:
    scope, identifier = None, None
    if scope_identifiers and len(scope_identifiers) > 1:
        raise MultipleScopeIdentifiersError(
            f"Multiple identifier names provided: {list(scope_identifiers.keys())}. "
            "Only one is allowed."
        )
    if scope_identifiers:
        (scope, identifier), = scope_identifiers.items()
    return scope, identifier


def get_config(
    data_store: DataStore,
    namespace: str,
    scope_identifiers: dict[ScopeName, str] | None = None,
    mode: str = "default",
    scope_ids_must_exist: set[ScopeName] | None = None,
    merge: bool = True,
) -> tuple[ConfigData, list[Path]]:
    """
    Get config data from store based on namespace and scopes.

    If mode is given, ficus will find the mode overrides (<mode>.yml) within each scope, and use 
    those values to override the default mode (default.yml) in each scope. If mode is None, just 
    default.yml will be used from each scope.

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
            The name of the configuration file (extension is ignored). If None,
            the default config file will be used.
        merge: bool
            Whether to merge config files found in each scope. If false, only the config file in
            the last scope from identifier names will be returned.

    Returns:
    --------
        tuple[ConfigData, list[Path]]
            A tuple containing the configuration data and a list of paths the config was made from.

    Raises:
    -------
        ConfigNotFoundError
            Raised if no configuration files are found for the given namespace and scope identifiers
    """
    config = {}
    try:
        file_override_paths = get_override_stack(data_store=data_store,
                                                      namespace=namespace,
                                                      scope_identifiers=scope_identifiers,
                                                      mode=mode,
                                                      scope_ids_must_exist=scope_ids_must_exist)
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
    data: dict,
    mode: str = "default",
    suffix: Optional[VALID_EXTENSIONS_TYPE] = None,
    overwrite: bool = False,
    create_missing_namespace: bool = True,
    create_missing_scope_id: bool = True,
    create_missing_scope: bool = False,
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

    Data will be saved to a valid yaml or json based on suffix

    Parameters: TODO: Update all docstrings
    -----------
        namespace
            The namespace for the configuration file.
        mode
            The name of the configuration file. Extension is optional. If specified,
            save to the preferred extension. If unspecified, save in the default
            format (yaml).
        data
            The configuration data to save.
        scope_identifier
            A dict, keyed by scope name, of identifiers per scope.
        overwrite
            Whether to overwrite the config file if it already exists (format agnostic).
            Error if file exists and `overwrite=False`
    Returns:
    --------
        tuple[dict, Path]
            A tuple containing the configuration data and the path the config was saved to.
    """
    if suffix is not None and suffix not in VALID_EXTENSIONS:
        raise UnsupportedFileTypeError(f"Cannot save {mode} to unknown format {suffix}.")

    scope, scope_id = _validate_single_scope(scope_identifier)
    paths = _get_all_search_paths(data_store, namespace, scope_identifier)
    _ensure_paths(data_store=data_store, paths=paths,
                  create_missing_namespace=create_missing_namespace,
                  scope_ids_must_exist={scope} if scope else None,
                  create_missing_scope_id=create_missing_scope_id,
                  create_missing_scope=create_missing_scope)

    target_folder = paths[-1]
    sibling_files = data_store.list_files(target_folder)
    mode_in_scope = [PurePath(f) for f in sibling_files if PurePath(f).stem == mode]

    paths_to_delete = []
    if mode_in_scope:
        if not overwrite:
            raise ConfigExistsError(f"Cannot overwrite config with mode '{mode}' in {target_folder} "
                                    "without overwrite=True")
        
        if suffix is None: # use the suffix of the existing file
            suffix = mode_in_scope[0].suffix
        elif suffix != mode_in_scope[0].suffix:
            logger.info(f"Changing file extension for config with mode '{mode}' in {target_folder}."
                           f"Previous format: {mode_in_scope[0].suffix}, new format: {suffix}.")
            paths_to_delete.extend([target_folder / f for f in mode_in_scope])
    elif suffix is None:
        suffix = DEFAULT_SUFFIX

    filepath = target_folder / Path(f"{mode}{suffix}")
    data_as_bytes = _validate_and_convert_to_bytes(suffix, data)
    if data_store.exists(filepath):
        data_store.update(filepath, data_as_bytes, force=True)
    else:
        data_store.create(filepath, data_as_bytes)

    # clean up the old version of the file with the old suffix, if it exists
    for path in paths_to_delete:
        data_store.delete(path)

    return data, filepath


def save_config_deep(
    data_store: DataStore,
    namespace: str,
    scope_identifiers: dict[ScopeName, str],
    data: dict,
    mode: str = DEFAULT_MODE,
    suffix: VALID_EXTENSIONS_TYPE | None = None,
    overwrite_defaults: bool = False,
    append_new_fields_to_last_scope: bool = False,
    create_missing_namespace: bool = True,
) -> dict:
    """Deep save config file by walking up the override hierarchy specified in
    scope_identifiers and saving fields back to the location where they were
    inserted.

    Parameters
    ----------
    namespace:
        the config namespace.
    mode:
        The mode of the configuration file. Typically "default".
    suffix:
        The file extension/suffix for the configuration file. Defaults to '.yml'.
    scope_identifiers:
        dict of scope identifiers sorted in lowest-override-priority to
        highest-override-priority.
    overwrite_defaults:
        If True allow writing to the defaults config of any scope.
        If False, put all fields that would be edited into the default file into
        a config named `<mode><suffix>` at the same scope. Create if missing.
    append_new_fields_to_last_scope:
        if new fields are created, append them at the lowest level scope.
        Error if new fields are created and this flag is set to False.
    """
    if suffix is not None and suffix not in VALID_EXTENSIONS:
        raise UnsupportedFileTypeError(f"Cannot save {mode + suffix} to unknown format.")
    override_stack = get_override_stack(data_store=data_store,
                                        namespace=namespace,
                                        scope_identifiers=scope_identifiers,
                                        mode=mode,
                                        must_exist_in_any_scope=False,
                                        must_exist_in_lowest_scope=False,
                                        create_missing_namespace=create_missing_namespace)
    if not override_stack:
        save_config(data_store=data_store, namespace=namespace, scope_identifier=None,
                    mode=mode, suffix=suffix, data=data, create_missing_namespace=create_missing_namespace)
        return
    # Convert all suffixes to the desired suffix.
    # (Flat save_config will convert the file format.)
    override_stack_new_suffix = copy.deepcopy(override_stack)
    for idx, filepath in enumerate(override_stack_new_suffix):
        if filepath.stem == mode:
            if suffix is None:
                suffix = filepath.suffix
            override_stack_new_suffix[idx] = filepath.with_suffix(suffix)
    if suffix is None:
        suffix = DEFAULT_SUFFIX
    # Cache new config values before writing to each file.
    new_cfg_data: dict[Path, dict] = {}
    # Walk up the override stack and save new field values to the respective
    # place they came from. Do this locally first to check if we have leftover data.
    data_cpy = copy.deepcopy(data)
    for idx, filepath in reversed(list(enumerate(override_stack_new_suffix))):
        filepath_old_suffix = override_stack[idx]
        old_level_cfg = _validate_and_convert_to_dict(filepath_old_suffix.suffix, 
                                                      data_store.read(filepath_old_suffix))
        level_cfg = copy.deepcopy(old_level_cfg)
        _deep_update_existing_destructive(level_cfg, data_cpy)
        # Nothing to save back if nothing actually changed.
        if old_level_cfg == level_cfg and filepath_old_suffix.suffix == filepath.suffix:
            continue
        # IF the data came from default.*, get a local copy of default.*,
        # save to filename at the same scope.
        if filepath.stem.lower() == DEFAULT_MODE and not overwrite_defaults:
            filepath = filepath.parent / (mode + suffix)
        # Respect override hierarchy if filename already exists at the scope that
        # defaults would go.
        if filepath in new_cfg_data:
            priority_cfg = new_cfg_data[filepath]
            level_cfg.update(priority_cfg)
        # Track new config to be written back in batch after-the-fact.
        new_cfg_data[filepath] = level_cfg
    # Do the writes in batch after checking if extra fields exist.
    # Put any new fields at the lowest level scope.
    if data_cpy: # data_cpy should be empty if all fields were found in the override stack.
        if append_new_fields_to_last_scope:
            if override_stack[-1] in new_cfg_data:
                new_cfg_data[override_stack[-1]].update(data_cpy)
            else:
                new_cfg_data[override_stack[-1]] = data_cpy
        else:
            raise ConfigMutatedError("Config to be saved has additional fields not "
                                     "previously found in the original config override "
                                     f"stack. New fields: {data_cpy}")

    for filepath, data in new_cfg_data.items():
        ns, scope_id, filename = _get_parts_from_path(data_store=data_store, path=filepath)
        tmp_mode, tmp_suffix = PurePath(filename).stem, PurePath(filename).suffix
        save_config(data_store=data_store, namespace=ns, scope_identifier=scope_id,
                    mode=tmp_mode, suffix=tmp_suffix, data=data, overwrite=True)
    return data_cpy


def update_config(
    data_store: DataStore,
    namespace: str,
    mode: str,
    data: dict,
    scope_identifier: dict[ScopeName, str],
    new_suffix: Optional[VALID_EXTENSIONS_TYPE] = None,
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

    raise NotImplementedError()

    config_data = get_config(...)
    config_data.update(data)
    save_config_deep(config_data)


    # FIXME: this is basically a save where the config must already exist.

    filepath = PurePath(filename) # convert for suffix
    scope, identifier = _validate_single_scope(scope_identifier)
    current_config, _ = get_config(
        data_store=data_store, namespace=namespace, mode=mode,
        scope_identifiers=scope_identifier, merge=False
    )
    # Throw away value, only want to validate
    _validate_and_convert_to_bytes(filepath.suffix, data=data)
    raw_config = _deep_update(current_config, data)
    return save_config(data_store=data_store,
                       namespace=namespace,
                       mode=mode,
                       data=raw_config,
                       scope_identifier=scope_identifier,
                       override=True,
                       create_missing_paths=False
                       )


def delete_config(
    data_store: DataStore, namespace: str, filename: str,
    scope_identifier: dict[ScopeName, str] | None = None
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
                                  scope_identifiers=scope_identifier)
    if len(paths) > 2:  # Should be at most default scope path and scoped path.
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


def delete_config_deep(
    data_store: DataStore,
    namespace: str,
    scope_identifiers: dict[ScopeName, str],
    filename: str,
    delete_defaults: bool = False,
):
    """Delete all configs with the specified name across all specified namespace and scopes.

    Parameters
    ----------
    namespace:
        the config namespace.
    filename:
        the config filename. Extension is ignored.
    scope_identifiers:
        dict of scope identifiers sorted in lowest-override-priority to
        highest-override-priority.
    override_defaults:
        If True allow writing to the defaults config of any scope.
        If False, put all fields that would be edited into the default file into
        a config named `filename` at the same scope. Create if missing.
    """
    file_as_path = PurePath(filename)
    override_stack = get_override_stack(data_store=data_store,
                                              namespace=namespace,
                                              scope_identifiers=scope_identifiers,
                                              filestem=file_as_path.stem)
    stems_to_delete = {file_as_path.stem} | ({"default"} if delete_defaults else set())
    # Walk up the override stack and delete
    for filepath in reversed(override_stack):
        if filepath.stem in stems_to_delete:
            ns, scope_id, filename = _get_parts_from_path(data_store=data_store,
                                                          path=filepath)
            delete_config(data_store=data_store, namespace=ns, scope_identifier=scope_id,
                          filename=filename)

def get_override_stack(
    data_store: DataStore,
    namespace: str,
    mode: str = "default",
    scope_identifiers: dict[ScopeName, str] | None = None,
    scope_ids_must_exist: set[ScopeName] | None = None,
    must_exist_in_any_scope: bool = True,
    must_exist_in_lowest_scope: bool = True,
    create_missing_namespace: bool = False,
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
        mode: str
            The name of the configuration mode (will match files like <mode>.yml)

    Returns:
    --------
        override_paths: list[Path]
            A list of paths to the files that apply to this config in reverse
            For example:
                [./defaults/software_a/default.yml, ./hostname/w11dt000001/software_a/default.yml]
                or, if mode is provided (not default):
                [./defaults/software_a/default.yml, 
                 ./defaults/software_a/mode.yml, 
                 ./hostname/w11dt000001/software_a/default.yml, 
                 ./hostname/w11dt000001/software_a/mode.yml]
            
    Raises:
    -------
        FileNotFoundError
            Raised if the must_exist_in_any_scope=True and mode is not found anywhere or
             if must_exist_in_lowest_scope=True and mode is not found in lowest scope.
        InvalidNamespaceError
            if the namespace does not exist.
        InvalidScopeError
            if a scope does not exist.
        InvalidScopeIdentifierError
            if a scope identifier does not exist.
    """
    # Warning: we don't check to see if multiple defaults are present.
    override_stack = []
    valid_filestems = {"default", mode}
    paths = _get_all_search_paths(data_store, namespace, scope_identifiers)
    # Make sure that paths exist in the data store
    paths = _ensure_paths(data_store=data_store, paths=paths,
                  create_missing_namespace=create_missing_namespace,
                  scope_ids_must_exist=scope_ids_must_exist)
    # Get defaults, followed by config name in each namespace.
    for folder_path in paths:
        # Sort alphabetized with defaults first.
        for found_file in sorted(data_store.list_files(folder_path),
                           key=lambda x: "" if Path(x).stem == DEFAULT_MODE else x.lower()):
            fp = Path(found_file)
            # Append default if it exists.
            if fp.stem in valid_filestems and ((not fp.suffix)
                                               or fp.suffix.lower() in VALID_EXTENSIONS):
                override_stack.append(folder_path / found_file)
    if must_exist_in_any_scope:
        found_filenames = [f.stem for f in override_stack]
        if mode not in found_filenames:
            raise FileNotFoundError()
    if must_exist_in_lowest_scope:
        if override_stack[-1].stem != mode:
            raise FileNotFoundError()
    return override_stack


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
