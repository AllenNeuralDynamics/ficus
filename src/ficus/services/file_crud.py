from ficus.database.data_store import DataStore
from ficus.services.utils import (
    DEFAULT_MODE,
    SUFFIX_STR_TYPE,
    _file_path_from_parts,
    _get_all_search_paths,
    _validate_and_convert_to_dict,
    _validate_and_convert_to_bytes,
)
from ficus.utils.dict_merge import _deep_update


def read_file(
    data_store: DataStore,
    namespace: str,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
) -> tuple[str, SUFFIX_STR_TYPE]:
    """Get a single leaf based on namespace, scope, and identifier.

    Parameters:
    -----------
        data_store: DataStore
            The data store instance where the configuration files are stored.
        namespace: str
            The namespace for the configuration file.
        scope: str | None
            The name of the scope. If None, the default scope is used.
        scope_identifier: str | None
            The identifier for the given scope. If None, the default scope is used.
        mode: str
            The mode of the configuration file (e.g., "default", "production").

    Returns:
    --------
        tuple[str, SUFFIX_STR_TYPE]
            A tuple containing the contents and the file suffix.

    Raises:
    -------
        FileNotFoundError
    """
    file = _file_path_from_parts(data_store, namespace, mode, scope, scope_identifier)
    content = data_store.read(file).decode()
    return content, file.suffix

def read_file_data(
    data_store: DataStore,
    namespace: str,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
) -> dict:
    content, suffix = read_file(data_store, namespace, scope, scope_identifier, mode)
    return _validate_and_convert_to_dict(suffix, content.encode())

def create_file(
    data_store: DataStore,
    namespace: str,
    suffix: SUFFIX_STR_TYPE,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
    content: str = "",
    overwrite: bool = False,
)-> str:
    """Create a single leaf based on namespace, mode, scope, and identifier."""
    scope_identifiers = {scope: scope_identifier} if scope is not None else None
    paths = _get_all_search_paths(data_store, namespace, scope_identifiers)
    folder = paths[-1]
    filename = f"{mode}{suffix}"
    file_path = folder / filename
    if data_store.exists(file_path):
        if not overwrite:
            raise FileExistsError(f"File already exists: {file_path}")
        else:
            data_store.update(file_path, content.encode())
    else:
        data_store.create(file_path, content.encode())
    return content

def create_file_from_data(
    data_store: DataStore,
    namespace: str,
    data: dict,
    suffix: SUFFIX_STR_TYPE,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
    overwrite: bool = False,
)-> str:
    return create_file(
        data_store=data_store,
        namespace=namespace,
        suffix=suffix,
        scope=scope,
        scope_identifier=scope_identifier,
        mode=mode,
        content=_validate_and_convert_to_bytes(suffix, data).decode(),
        overwrite=overwrite,
    )

def update_file_data(
    data_store: DataStore,
    namespace: str,
    data: dict,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
) -> dict:
    content, suffix = read_file(data_store, namespace, scope, scope_identifier, mode)
    current_data = _validate_and_convert_to_dict(suffix, content.encode())
    updated_data = _deep_update(current_data, data)
    updated_content = create_file_from_data(
        data_store=data_store,
        namespace=namespace,
        data=updated_data,
        suffix=suffix,
        scope=scope,
        scope_identifier=scope_identifier,
        mode=mode,
        overwrite=True,
    )
    return _validate_and_convert_to_dict(suffix, updated_content.encode())

def delete_file(
    data_store: DataStore,
    namespace: str,
    scope: str | None = None,
    scope_identifier: str | None = None,
    mode: str = DEFAULT_MODE,
):
    file = _file_path_from_parts(data_store, namespace, mode, scope, scope_identifier)
    data_store.delete(file)
