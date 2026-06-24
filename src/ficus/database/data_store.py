from abc import ABC, abstractmethod
from pathlib import Path


class DataStore(ABC):
    """Base Class for interacting with generic storage: Folders, Database, etc.
    """

    def __init__(self, rootdir: Path | str):
        self.rootdir = Path(rootdir)

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

    # crud functions
    @abstractmethod
    def create(self, path: Path | str, data: bytes) -> None:
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
