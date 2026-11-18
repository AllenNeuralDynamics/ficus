from pathlib import Path

from ficus.database.data_store import DataStore
from ficus.services.configs import get_config, save_config
from ficus.services.utils import _validate_and_convert_to_bytes, _validate_and_convert_to_dict
from ficus.utils.dict_merge import _deep_update


class PreviewStore(DataStore):
    """Keep proposed writes in memory while reading unchanged files from the real store."""

    def __init__(self, source: DataStore):
        self.source = source
        self.rootdir = source.rootdir
        self.scopes = source.scopes
        self.files: dict[Path, bytes | None] = {}
        self.directories: set[Path] = set()

    def exists(self, path: Path | str) -> bool:
        path = self._sanitize(path)
        if path in self.files:
            return self.files[path] is not None
        return path in self.directories or self.source.exists(path)

    def create(self, path: Path | str, data: bytes | None) -> None:
        path = self._sanitize(path)
        if data is None:
            self.directories.add(path)
        else:
            self.files[path] = data
            self.directories.update(path.parents)

    def read(self, path: Path | str) -> bytes:
        path = self._sanitize(path)
        if path in self.files:
            if self.files[path] is None:
                raise FileNotFoundError(path)
            return self.files[path]
        return self.source.read(path)

    def update(self, path: Path | str, data: bytes, force: bool = False) -> None:
        path = self._sanitize(path)
        if not self.exists(path) and not force:
            raise FileNotFoundError(path)
        self.files[path] = data

    def delete(self, path: Path | str, recursive: bool = False) -> None:
        path = self._sanitize(path)
        if not self.exists(path):
            raise FileNotFoundError(path)
        self.files[path] = None

    def list_files(self, path: Path | str) -> list[str]:
        path = self._sanitize(path)
        existing = set(self.source.list_files(path)) if self.source.exists(path) else set()
        for file_path, data in self.files.items():
            if file_path.parent == path:
                if data is None:
                    existing.discard(file_path.name)
                else:
                    existing.add(file_path.name)
        return sorted(existing)

    def list_directories(self, path: Path | str) -> list[str]:
        path = self._sanitize(path)
        list_source = getattr(self.source, "list_directories", None)
        existing = set(list_source(path)) if list_source and self.source.exists(path) else set()
        existing.update(directory.name for directory in self.directories if directory.parent == path)
        return sorted(existing)


def preview_config(
    data_store: DataStore,
    namespace: str,
    path: Path,
    data: dict,
    mode: str,
    scope_identifiers: dict[str, str],
):
    config = get_config(data_store, namespace, mode=mode, scope_identifiers=scope_identifiers)
    if path not in config.override_stack:
        raise ValueError(f"Path is not in the config override stack: {path}")
    overlay = PreviewStore(data_store)
    existing = _validate_and_convert_to_dict(path.suffix, data_store.read(path))
    overlay.update(path, _validate_and_convert_to_bytes(path.suffix, _deep_update(existing, data)))
    return get_config(overlay, namespace, mode=mode, scope_identifiers=scope_identifiers)


def dry_run_save_config(data_store: DataStore, **save_options) -> list[dict]:
    overlay = PreviewStore(data_store)
    save_config(overlay, **save_options)
    changes = []
    for path, proposed in overlay.files.items():
        previous = data_store.read(path) if data_store.exists(path) else None
        if previous == proposed:
            continue
        changes.append({
            "path": str(path),
            "before": _validate_and_convert_to_dict(path.suffix, previous) if previous else None,
            "after": _validate_and_convert_to_dict(path.suffix, proposed) if proposed else None,
        })
    return changes
