from ficus.core.exceptions import PathIsDirectoryError, PathNotFoundError
from ficus.database.data_store import DataStore
from loguru import logger
from pathlib import Path

import stat


def ensure_write_permission(folder_path: str | Path):
    # ai-generated function to ensure folder has write permission.

    path = Path(folder_path)

    if not path.exists():
        raise FileNotFoundError(f"The path {path} does not exist.")
    if not path.is_dir():
        raise NotADirectoryError(f"The path {path} is not a directory.")

    # Get current permission bits
    current_mode = path.stat().st_mode

    # Define required permissions (Owner Read, Write, and Execute)
    required_permissions = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR

    # Check if the required permissions are already set
    if (current_mode & required_permissions) != required_permissions:
        # Bitwise OR merges existing permissions with the missing ones
        new_mode = current_mode | required_permissions
        path.chmod(new_mode)
        logger.debug(f"Permissions updated for: {path}")
    else:
        logger.debug(f"Write permissions are already granted for: {path}")

# FIXME: Validation to ensure scopes are present?

class FileSysStore(DataStore):

    def __init__(self, rootdir: Path | str):
        self.log = logger.bind(custom_name=self.__class__.__name__)
        ensure_write_permission(rootdir)
        super().__init__(rootdir=rootdir)

    def create(self, path: Path | str, data: bytes) -> None:
        path = self._sanitize(path)
        if path.exists():
            raise FileExistsError(f"File already exists at: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, path: Path | str) -> bytes:
        path = self._sanitize(path)
        if not path.exists():
            raise PathNotFoundError(f"File does not exist at: {path}")
        if not path.is_file():
            raise ValueError(f"Cannot read file data from path: {path}")
        return path.read_bytes()

    def update(self, path: Path | str, data: bytes, force: bool = False) -> None:
        path = self._sanitize(path)
        if not path.exists():
            raise PathNotFoundError(f"File does not exist at: {path}")
        if not path.is_file():
            raise PathIsDirectoryError(f"Cannot write data to non-file path: {path}")
        path.write_bytes(data)  # complete overwrite.

    def delete(self, path: Path | str, recursive: bool = False) -> None:
        path = self._sanitize(path)
        if not path.exists():
            raise PathNotFoundError(f"Cannot delete content at nonexistent path: {path}")
        if not path.is_file():
            raise PathIsDirectoryError(f"Path {path} points to directory, not file.")
        path.unlink()

    def exists(self, path: Path | str) -> bool:
        path = self._sanitize(path)
        return path.exists()

    def list_files(self, path: Path | str) -> list[str]:
        path = self._sanitize(path)
        if path.is_file():
            raise ValueError(f"Cannot list files on a file: {path}")
        return [item.name for item in path.iterdir() if item.is_file()]
