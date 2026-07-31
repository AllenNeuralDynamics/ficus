import copy
from typing import Optional
from loguru import logger
from ficus.utils.dict_merge import _deep_update, _deep_update_existing_destructive


from ficus.core.exceptions import (
    ConfigExistsError,
    ConfigMutatedError,
    ConfigNotFoundError,
    PathNotFoundError,
    UnsupportedFileTypeError,
)
from ficus.database.data_store import DataStore
from ficus.schemas.configs import ConfigObject
from pathlib import Path, PurePath
from ficus.services.utils import (
    DEFAULT_MODE,
    VALID_EXTENSIONS_TYPE,
    VALID_EXTENSIONS,
    DEFAULT_SUFFIX,
    ScopeName,
    _ensure_paths,
    _find_first_invalid_subpath,
    _get_all_search_paths,
    _get_parts_from_path,
    _validate_and_convert_to_bytes,
    _validate_and_convert_to_dict,
    _validate_single_scope,
)

## Config CRUD methods

def get_config(
    data_store: DataStore,
    namespace: str,
    scope_identifiers: dict[ScopeName, str] | None = None,
    mode: str = "default",
    scope_ids_must_exist: set[ScopeName] | None = None,
) -> ConfigObject:
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
        mode: str
            The configuration mode (matches files like <mode>.yml). Defaults to
            "default".
        scope_ids_must_exist: set[ScopeName] | None
            Scopes whose identifier folders are required to exist. A missing
            identifier for one of these scopes raises InvalidScopeIdentifierError.
        merge: bool
            Whether to merge config files found in each scope. If false, only the config file in
            the last scope from identifier names will be returned.

    Returns:
    --------
        ConfigObject
            An object with data and metadata from a config

    Raises:
    -------
        ConfigNotFoundError
            if no configuration files are found for the given namespace and mode.
        InvalidNamespaceError
            if the namespace does not exist.
        InvalidScopeError
            if a scope does not exist.
        InvalidScopeIdentifierError
            if a required scope identifier does not exist.
    """
    cfg_not_found_msg = f"Could not find config: {mode}.{list(VALID_EXTENSIONS)}"
    try:
        file_override_paths = get_override_stack(data_store=data_store,
                                                      namespace=namespace,
                                                      scope_identifiers=scope_identifiers,
                                                      mode=mode,
                                                      scope_ids_must_exist=scope_ids_must_exist)
    except FileNotFoundError:
        raise ConfigNotFoundError(cfg_not_found_msg)
    if not file_override_paths:
        raise ConfigNotFoundError(cfg_not_found_msg)
    config = ConfigObject(
        data = {},
        namespace = namespace,
        mode = mode,
        scope_identifiers = scope_identifiers or {},
        override_stack = file_override_paths
    )
    # Iterate backwards so we can return immediately if not merging.
    for filepath in reversed(file_override_paths):
        override_data_bytes = data_store.read(filepath)
        override_data = _validate_and_convert_to_dict(filepath.suffix, override_data_bytes)
        config.data = _deep_update(override_data, config.data)

    return config


def _save_one_config_override( #TODO: refactor to use file_crud methods
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

    If scope and/or identifier do not exist, they are created according to the
    `create_missing_namespace`, `create_missing_scope_id`, and
    `create_missing_scope` flags. Otherwise a corresponding error is raised.

    Identifier names are expected to correspond to a scope (auto-validates this). The function will
    also expect to be given a single identifier name since a config file can only be saved to one
    scope.

    Data will be saved to a valid yaml or json based on suffix

    Parameters:
    -----------
        data_store: DataStore
            The data store instance where the configuration files are stored.
        namespace: str
            The namespace for the configuration file.
        scope_identifier: dict[ScopeName, str]
            A dict, keyed by scope name, of identifiers per scope.
        data: dict
            The configuration data to save.
        mode: str
            The name of the configuration file (extension excluded). Defaults to
            "default".
        suffix: Optional[VALID_EXTENSIONS_TYPE]
            The file extension to save to (".yml", ".yaml", or ".json"). If None,
            reuse the existing file's suffix when overwriting, otherwise default
            to ".yml".
        overwrite: bool
            Whether to overwrite the config file if it already exists (format agnostic).
            Error if file exists and `overwrite=False`
        create_missing_namespace: bool
            Create the namespace under defaults if it does not exist.
        create_missing_scope_id: bool
            Create the scope identifier folder if it does not exist.
        create_missing_scope: bool
            Create the scope if it does not exist.
    Returns:
    --------
        tuple[dict, Path]
            A tuple containing the configuration data and the path the config was saved to.

    Raises:
    -------
        UnsupportedFileTypeError
            if `suffix` is not a supported extension.
        ConfigExistsError
            if the config already exists and `overwrite=False`.
        InvalidNamespaceError
            if the namespace does not exist and `create_missing_namespace=False`.
        InvalidScopeError
            if a scope does not exist and `create_missing_scope=False`.
        InvalidScopeIdentifierError
            if a scope identifier does not exist and `create_missing_scope_id=False`.
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
            raise ConfigExistsError(f"Cannot overwrite config with mode '{mode}' in {target_folder}"
                                    " without overwrite=True")

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


def save_config(
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
    data_store: DataStore
        The data store instance where the configuration files are stored.
    namespace: str
        the config namespace.
    scope_identifiers: dict[ScopeName, str]
        dict of scope identifiers sorted in lowest-override-priority to
        highest-override-priority.
    data: dict
        The configuration data to be saved.
    mode: str
        The mode of the configuration file. Typically "default".
    suffix: VALID_EXTENSIONS_TYPE | None
        The file extension/suffix for the configuration file. Defaults to '.yml'.
    overwrite_defaults: bool
        If True allow writing to the defaults config of any scope.
        If False, put all fields that would be edited into the default file into
        a config named `<mode><suffix>` at the same scope. Create if missing.
    append_new_fields_to_last_scope: bool
        if new fields are created, append them at the lowest level scope.
        Error if new fields are created and this flag is set to False.
    create_missing_namespace: bool
        If True, create the namespace in the default scope of the data store if it
        does not already exist.

    Returns
    -------
    dict
        Leftover fields that were not saved into the config stack.

    Raises
    ------
    UnsupportedFileTypeError
        Raised if the provided suffix is not in the list of valid extensions.
    ConfigMutatedError
        Raised if the configuration data has new fields and
        `append_new_fields_to_last_scope` is False.
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
        _save_one_config_override(data_store=data_store, namespace=namespace, scope_identifier=None,
                    mode=mode, suffix=suffix, data=data,
                    create_missing_namespace=create_missing_namespace)
        return
    # Convert all suffixes to the desired suffix.
    # (Flat _save_one_config_override will convert the file format.)
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
                                     f"stack, and append_new_fields_to_last_scope is False. "
                                     f"New fields: {data_cpy}")

    for filepath, data in new_cfg_data.items():
        ns, scope_id, filename = _get_parts_from_path(data_store=data_store, path=filepath)
        tmp_mode, tmp_suffix = PurePath(filename).stem, PurePath(filename).suffix
        _save_one_config_override(data_store=data_store, namespace=ns, scope_identifier=scope_id,
                    mode=tmp_mode, suffix=tmp_suffix, data=data, overwrite=True)
    return data_cpy


def update_config(
    data_store: DataStore,
    namespace: str,
    mode: str = DEFAULT_MODE,
    scope_identifiers: dict[ScopeName, str] | None = None,
    data: dict | None = None,
    new_suffix: str = DEFAULT_SUFFIX,
    overwrite_defaults: bool = False,
    append_new_fields_to_last_scope: bool = False,
) -> dict:
    """
    Deep update config file based on namespace, scope, and identifier; allows saving partial data.

    This function will get the existing config (complete with merged overrides),
     update it with the new data given, then deep save back to the override stack.

    Parameters:
    -----------
        data_store: DataStore
            The data store instance to interact with the underlying storage.
        namespace: str
            The namespace for the configuration file.
        mode: str
            The mode of the configuration file (e.g., "default", "production").
        scope_identifiers: dict[ScopeName, str]
            A dict, keyed by scope name, of identifiers per scope.
        data: dict
            The configuration data to update.
        new_suffix: str
            The suffix to use when saving the updated configuration file.
        overwrite_defaults: bool
            Whether to overwrite default configurations if they exist.
        append_new_fields_to_last_scope: bool
            Whether to append new fields to the last scope in the override stack.

    Returns:
    --------
        dict
            Leftover fields that were not merged into the existing configuration.
    """

    config = get_config(data_store=data_store, namespace=namespace, mode=mode,
                             scope_identifiers=scope_identifiers)
    updated_data = _deep_update(config.data, data)
    return save_config(data=updated_data, data_store=data_store, namespace=namespace, mode=mode,
                     scope_identifiers=scope_identifiers, suffix=new_suffix,
                     overwrite_defaults=overwrite_defaults,
                     append_new_fields_to_last_scope=append_new_fields_to_last_scope)


def _delete_one_config_override( # TODO: refactor to use file_crud methods
    data_store: DataStore, namespace: str, mode: str = DEFAULT_MODE,
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
        mode: str
            The mode of the configuration file (e.g., "default", "production").
        scope_identifier: dict[ScopeName, str]
            A dict, keyed by scope name, of identifiers per scope.

    Returns:
    --------
        str
            The path of the deleted config file.
    """

    scope, _ = _validate_single_scope(scope_identifier)
    paths = _get_all_search_paths(data_store=data_store, namespace=namespace,
                                  scope_identifiers=scope_identifier)
    paths = _ensure_paths(data_store, paths, scope_ids_must_exist={scope})
    lowest_path = paths[-1]
    files = [f for f in data_store.list_files(lowest_path) if PurePath(f).stem == mode]
    if not files:
        raise ConfigNotFoundError(f"Config file not found for mode '{mode}' in path: {lowest_path}")
    filename = files[0]
    path = lowest_path / filename
    try:
        data_store.delete(path)
        return str(path)
    except PathNotFoundError:
        invalid_subpath = _find_first_invalid_subpath(data_store, path)
        if invalid_subpath:
            raise ConfigNotFoundError(f"Subpath '{invalid_subpath}' not found in path: {path}")
        raise ConfigNotFoundError(f"Config file not found at path: {path}")


def delete_config(
    data_store: DataStore,
    namespace: str,
    scope_identifiers: dict[ScopeName, str],
    mode: str = DEFAULT_MODE,
    delete_defaults: bool = False,
):
    """Delete all configs with the specified name across all specified namespace and scopes.

    Parameters
    ----------
    data_store: DataStore
        The data store instance where the configuration files are stored.
    namespace: str
        the config namespace.
    scope_identifiers: dict[ScopeName, str]
        dict of scope identifiers sorted in lowest-override-priority to
        highest-override-priority.
    mode: str
        the config mode. Extension is ignored.
    delete_defaults: bool
        If True, also delete the default config file for the given mode in each scope.
        If False, only delete the specified mode in the override stack, leaving the default config intact.
    """
    override_stack = get_override_stack(data_store=data_store,
                                              namespace=namespace,
                                              scope_identifiers=scope_identifiers,
                                              mode=mode)
    stems_to_delete = {mode} | ({"default"} if delete_defaults else set())
    # Walk up the override stack and delete
    for filepath in reversed(override_stack):
        if filepath.stem in stems_to_delete:
            ns, scope_id, filename = _get_parts_from_path(data_store=data_store,
                                                          path=filepath)
            _delete_one_config_override(data_store=data_store, namespace=ns, scope_identifier=scope_id,
                          mode=Path(filename).stem)


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
    """For a given namespace, scope_identifiers, and mode, return the full
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
        scope_ids_must_exist: set[ScopeName] | None
            Scopes whose identifier folders are required to exist. A missing
            identifier for one of these scopes raises InvalidScopeIdentifierError.
        must_exist_in_any_scope: bool
            If True, the mode must exist in at least one scope, otherwise a FileNotFoundError is raised.
        must_exist_in_lowest_scope: bool
            If True, the mode must exist in the lowest scope, otherwise a FileNotFoundError is raised.
        create_missing_namespace: bool
            If True, create the namespace folder if it does not exist.

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
    valid_filestems = {DEFAULT_MODE, mode}
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


def get_all_modes(
    data_store: DataStore,
    namespace: str,
    scope_identifiers: dict[ScopeName, str] | None = None,
    scope_ids_must_exist: set[ScopeName] | None = None,
    lowest_scope_only: bool = True
) -> set[str]:
    """Get all modes for the given namespace and scope identifiers.

    Parameters:
    -----------
        data_store: DataStore
            storage location to search.
        namespace: str
            The namespace for the configuration files.
        scope_identifiers: dict[ScopeName, str]
            A dict, keyed by scope name, of identifiers per scope to filter by.
            If None are provided, only include the default scope.
        scope_ids_must_exist: set[ScopeName] | None
            Scopes whose identifier folders are required to exist. A missing
            identifier for one of these scopes raises InvalidScopeIdentifierError.
        lowest_scope_only: bool
            if True, only return modes present in the lowest scope. Otherwise,
            return modes found in any scope.

    Returns:
    --------
        a list of modes.

    Raises:
    -------
        InvalidNamespaceError
            if the namespace does not exist.
        InvalidScopeError
            if a scope does not exist.
        InvalidScopeIdentifierError
            if a scope identifier does not exist.
    """
    found_modes = set()
    paths = _get_all_search_paths(data_store, namespace, scope_identifiers)
    # Make sure that paths exist in the data store
    paths = _ensure_paths(data_store=data_store, paths=paths,
                          create_missing_namespace=False,
                          scope_ids_must_exist=scope_ids_must_exist)
    # Get defaults, followed by config name in each namespace.
    for folder_path in reversed(paths):
        # Sort alphabetized with defaults first.
        for found_file in data_store.list_files(folder_path):
            fp = Path(found_file)
            # Append valid mode.
            if ((not fp.suffix) or fp.suffix.lower() in VALID_EXTENSIONS):
                found_modes.add(fp.stem)
        if lowest_scope_only:
            break
    return found_modes
