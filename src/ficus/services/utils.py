import copy
import json
from typing import Annotated, Literal
from loguru import logger
import yaml

from pydantic import StringConstraints

from ficus.core.exceptions import (
    ConfigDecodeError,
    ConfigSerializeError,
    InvalidNamespaceError,
    InvalidScopeIdentifierError,
    MultipleScopeIdentifiersError,
    UnsupportedFileTypeError,
)
from ficus.database.data_store import DataStore
from pathlib import Path, PurePath

DEFAULT_MODE = "default"
SUFFIX_STR_TYPE = Annotated[str, StringConstraints(pattern=r"^\.")]
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

    No validation is performed that these paths are valid or exist.

    Parameters
    ----------
    data_store: DataStore
        The data store instance where the configuration files are stored.
    namespace: str | None
        The namespace for which to get search paths. If None, only scope paths are returned.
    scope_identifiers: dict[ScopeName, str] | None
        A dictionary of scope names to their identifiers to include in the search paths. If None, only the default scope is considered.

    Returns
    -------
    list[Path]
        A list of folder paths for the specified namespace and scope identifiers, in merge priority order (highest to lowest).
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
    paths: list[Path],
    create_missing_namespace: bool = False,
    scope_ids_must_exist: set[ScopeName] | None = None,
    create_missing_scope_id: bool = False,
    create_missing_scope: bool = False,
) -> list[Path]:
    """Create underlying data store structure to guarantee that the given
    `paths` (namespace and scope identifier folders) exist, and return the
    subset of paths that now exist. Call this function after _get_all_search_paths.

    Parameters
    ----------
    data_store: DataStore
        The data store instance where the configuration files are stored.
    paths: list[Path]
        The list of paths (namespace and scope identifier folders) to ensure exist.
    create_missing_namespace: bool
        If True, create the namespace folder if it does not exist. Default is False.
    scope_ids_must_exist: set[ScopeName] | None
        Scopes whose identifier folders are required to exist. A missing identifier for one of these scopes raises InvalidScopeIdentifierError. Default is None.
    create_missing_scope_id: bool
        If True, create missing scope identifier folders. Default is False.
    create_missing_scope: bool
        If True, create missing scope folders. Default is False.

    Returns
    -------
    ensured_paths: list[Path]
        The subset of the input `paths` that now exist in the data store after ensuring the necessary structure.

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
                    raise InvalidScopeIdentifierError(
                        f"Scope identifier not found: {scope}/{identifier}"
                    )
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
    """Ensure that the scope_identifiers dict contains at most one item"""
    scope, identifier = None, None
    if scope_identifiers and len(scope_identifiers) > 1:
        raise MultipleScopeIdentifiersError(
            f"Multiple identifier names provided: {list(scope_identifiers.keys())}. "
            "Only one is allowed."
        )
    if scope_identifiers:
        (scope, identifier), = scope_identifiers.items()
    return scope, identifier


def _file_path_from_parts(
    data_store: DataStore, 
    namespace: str, 
    mode: str = DEFAULT_MODE,
    scope: str | None = None,
    scope_identifier: str | None = None,
    ) -> Path:
    """Given a namespace, mode, scope, and identifier, return the full path to the file in the data store."""
    scope_identifiers = {scope: scope_identifier} if scope is not None else None
    paths = _get_all_search_paths(data_store, namespace, scope_identifiers)
    folder = paths[-1]
    files = data_store.list_files(folder)
    mode_files = [PurePath(f) for f in files if PurePath(f).stem == mode]
    if not mode_files:
        raise FileNotFoundError(f"No file found for mode '{mode}' in path: {folder}")
    mode_file = mode_files[0]
    return folder / mode_file


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
