#from contextlib import contextmanager

from fastapi import Request
from fastapi.responses import JSONResponse
from kazoo.client import KazooClient
from kazoo.handlers.threading import KazooTimeoutError
from kazoo.exceptions import NotEmptyError as ZKNotEmptyError
from kazoo.exceptions import BadVersionError as ZKBadVersionError
from ficus.core.exceptions import NotEmptyError, BadVersionError, PathNotFoundError
from kazoo.recipe.watchers import NoNodeError
from loguru import logger
from pathlib import Path
from threading import Lock

from ficus.database.data_store import DataStore

class ZKClientContextManager:
    """Reentrant context manager to manage one zookeeper connection with nested
    connection calls."""

    def __init__(self, hosts: list[str]):
        self._depth: int = 0 # Tracks the nesting level.
        self._lock: Lock = Lock()
        self.hosts: list[str] = hosts
        self._zk: KazooClient | None = None

    def __enter__(self):
        with self._lock:
            if self._depth == 0:
                self._zk = KazooClient(hosts=",".join(self.hosts))
                self._zk.start()

            self._depth += 1
            return self._zk

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self._lock:
            self._depth -= 1

            if self._depth == 0:
                self._zk.stop()
                self._zk.close()
                self._zk = None

        # Return False to let exceptions propagate normally
        return False


class ZKStore(DataStore):
    """CRUD functions for Zookeeper-based data store."""

    def __init__(self, hosts: list[str], rootdir: Path | str, scopes: set[str],
                 create_missing_scopes: bool = True):
        """
        Parameters
        ----------
        hosts:
            list of hosts. ex: `["127.0.0.1:8000", "127.0.0.1:9000"]`
        """
        self.log = logger.bind(custom_name=self.__class__.__name__)
        self.hosts = hosts
        self._path_versions = {}  # dict of all file reads to track versions
                                  # when calling update() on the same path.
        super().__init__(rootdir=rootdir, scopes=scopes,
                         create_missing_scopes=create_missing_scopes)

    # crud functions
    def create(self, path: Path | str, data: bytes | None) -> None:
        path = self._sanitize(path)
        with ZKClientContextManager(self.hosts) as zk:
            if self.exists(path) and self.is_file(path):
                raise NotEmptyError(f"Path {path} already exists.")
            if data is None:  # assume path is folder.
                zk.ensure_path(path.as_posix())
                return
            zk.create(path.as_posix(), data, makepath=True)

    def read(self, path: Path | str) -> bytes:
        path = self._sanitize(path)
        with ZKClientContextManager(self.hosts) as zk:
            data = None
            try:
                data, stat = zk.get(path.as_posix())
                # Save stat to check if the path was altered when we try an update later.
                self._path_versions[path.as_posix()] = stat
                return data
            except NoNodeError:
                raise PathNotFoundError(f"Path: {path} does not exist.")

    def update(self, path: Path | str, data: bytes, force: bool = False) -> None:
        path = self._sanitize(path)
        with ZKClientContextManager(self.hosts) as zk:
            # force if specified, or if we've never read the data in the first place.
            version = -1 if force else self._path_versions.get(path.as_posix(), -1)
            try:
                zk.set(path.as_posix(), data, version=version)
            except ZKBadVersionError:
                raise BadVersionError(f"Content at {path} has been updated by "
                                      f"another entity since reading.")

    def delete(self, path: Path | str, recursive: bool = False) -> None:
        path = self._sanitize(path)
        with ZKClientContextManager(self.hosts) as zk:
            try:
                zk.delete(path.as_posix(), recursive=recursive)
            except ZKNotEmptyError:
                raise NotEmptyError(f"Failed to delete. Node contains children: {path}")
            except NoNodeError:
                raise PathNotFoundError(f"Failed to delete. Path {path} is invalid.")

    # utility
    def exists(self, path: Path | str) -> bool:
        path = self._sanitize(path)
        with ZKClientContextManager(self.hosts) as zk:
            exists = zk.exists(path.as_posix())
            return exists
            #return zk.exists(path.as_posix())

    def is_file(self, path: Path | str) -> bool:
        path = self._sanitize(path)
        with ZKClientContextManager(self.hosts) as zk:
            data, _ = zk.get(path.as_posix())
            children: list = zk.get_children(path.as_posix())
            is_file = len(children) == 0 and len(data) > 0
            return is_file

    def list_files(self, path: Path | str) -> list[str]:
        path = self._sanitize(path)
        with ZKClientContextManager(self.hosts) as zk:
            if self.is_file(path):
                raise ValueError(f"Cannot list files on a file: {path}")
            children: list = zk.get_children(path.as_posix())
            return children





async def kazoo_timeout_handler(request: Request, exc: KazooTimeoutError):
    return JSONResponse(
        status_code=503, content={"message": "Zookeeper connection timed out, service unavailable"}
    )
