from ficus.database.data_store import DataStore


def list_namespaces(data_store: DataStore) -> list[str]:
    return sorted(data_store.list_directories(data_store.rootdir / "defaults"))


def list_scope_identifiers(
    data_store: DataStore, scope: str, namespace: str | None = None
) -> list[str]:
    if scope not in data_store.scopes:
        raise ValueError(f"Unknown scope: {scope}")
    identifiers = data_store.list_directories(data_store.rootdir / scope)
    if namespace is not None:
        identifiers = [
            identifier for identifier in identifiers
            if data_store.exists(data_store.rootdir / scope / identifier / namespace)
            and data_store.list_files(data_store.rootdir / scope / identifier / namespace)
        ]
    return sorted(identifiers)
