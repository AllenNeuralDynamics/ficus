from abc import ABC, abstractmethod
from pathlib import Path


class DataStore(ABC):
    """Base Class for interacting with generic storage: Folders, Database, etc.
    """

    def __init__(self, rootdir: Path | str):
        self.rootdir = Path(rootdir)

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
        pass

    @abstractmethod
    def list_files(self, path: Path | str) -> list[str]:
        pass
