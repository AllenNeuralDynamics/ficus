import json
from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path

from ficus.core.exceptions import InvalidScopeError

# Where a store keeps its scope precedence once a scope has been added through the API.
SCOPE_REGISTRY = Path(".ficus") / "scopes.json"
# Without a registry, the seed's order; a seed given as a set (no order) puts these first.
DEFAULT_PRECEDENCE = ("hostname", "subject_id")


def ordered_scopes(scopes: Iterable[str]) -> list[str]:
    """A seed as an ordered list: lists keep their order; sets put the AIND scopes first."""
    if isinstance(scopes, (list, tuple)):
        return list(dict.fromkeys(scopes))
    rank = {name: i for i, name in enumerate(DEFAULT_PRECEDENCE)}
    return sorted(set(scopes), key=lambda s: (rank.get(s, len(rank)), s))

class DataStore(ABC):
    """Base Class for interacting with generic storage: Folders, Database, etc.
    """

    def __init__(self, rootdir: Path | str, scopes: Iterable[str],
                 create_missing_scopes: bool = True):
        self.rootdir: Path = Path(rootdir)
        self._seed: list[str] = ordered_scopes(scopes)
        self.scope_order: list[str] = list(self._seed)
        self.reload_scopes()
        self.validate_scopes(set(self.scope_order), create_missing=create_missing_scopes)

    @property
    def scopes(self) -> set[str]:
        """The scopes this store knows (see scope_order for their precedence)."""
        return set(self.scope_order)

    def reload_scopes(self) -> list[str]:
        """Read the precedence: the registry if any (plus seed scopes it lacks), else the seed.

        Scopes merge in this order, lowest first, whatever order a request lists them in.
        """
        order = list(self._seed)
        registry = self.rootdir / SCOPE_REGISTRY
        if self.exists(registry):
            stored = json.loads(self.read(registry).decode("utf-8"))
            order = list(dict.fromkeys(stored)) + [s for s in self._seed if s not in stored]
        self.scope_order = order
        return order

    def write_scope_order(self, order: list[str]) -> None:
        """Persist the precedence (only done when a scope is added through the API)."""
        registry = self.rootdir / SCOPE_REGISTRY
        data = json.dumps(order).encode("utf-8")
        if self.exists(registry):
            self.update(registry, data, force=True)
        else:
            self.create(registry, data)
        self.scope_order = list(order)

    def _sanitize(self, path: str | Path) -> Path:
        """Coax path into path that is relative to self.rootdir.

        Raises
        ------
        ValueError:
            if the path is absolute and not a subpath of `self.rootdir`
        """
        path = Path(path)
        # Absolute path cases
        if path.is_relative_to(self.rootdir): # path is absolute.
            return path
        if path.is_absolute():
            raise ValueError(f"input paths specified as absolute paths must be "
                             f"relative to rootdir: {self.rootdir}. Input path: "
                             f"{path.absolute()}")
        # Relative path cases.
        return self.rootdir / path

    def validate_scopes(self, scopes: set[str], create_missing: bool = True):
        """ Ensures scopes exist in the store."""
        missing_scopes = set()
        for scope in scopes:
            scope_path = self.rootdir / Path(scope)
            if not self.exists(self.rootdir / Path(scope)):
                if create_missing:
                    self.create(scope_path, data=None)
                missing_scopes.add(scope)
        if missing_scopes and not create_missing:
                raise InvalidScopeError(f"The following scopes are missing from the "
                                   f"data store: {missing_scopes}")

    # crud functions
    @abstractmethod
    def create(self, path: Path | str, data: bytes | None) -> None:
        """Create the path specified.

        Parameters
        ----------
        path:
            path to file or folder.
        data:
            If data is `None` assume the path is a folder. If data is bytes-like
            (including empty bytes), create the file with the data specified.
        """
        pass

    @abstractmethod
    def read(self, path: Path | str) -> bytes:
        pass

    @abstractmethod
    def update(self, path: Path | str, data: bytes, force: bool = False) -> None:
        """
        Raises
        ------
        ficus.core.exceptions.BadVersionError
            if the path has been altered by external entity since being read.
        """
        pass

    @abstractmethod
    def delete(self, path: Path | str, recursive: bool = False) -> None:
        """delete the path specified.

        Raises
        ------
        ficus.core.exceptions.NotEmptyError
            if not `recursive` and path contains children (folders, files)
        """
        pass

    # utility
    @abstractmethod
    def exists(self, path: Path | str) -> bool:
        """True if the path specified (folder or file) exists."""
        pass

    @abstractmethod
    def list_files(self, path: Path | str) -> list[str]:
        pass

    @abstractmethod
    def list_directories(self, path: Path | str) -> list[str]:
        pass
