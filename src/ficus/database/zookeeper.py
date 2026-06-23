from contextlib import contextmanager

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

from ficus.core.config import settings
from ficus.database.data_store import DataStore


# FIXME: Validation to ensure scopes are present?

class ZKStore(DataStore):
    """CRUD functions for Zookeeper-based data store."""

    @contextmanager
    def _get_zk_client(self):
        """Context manager for KazooClient connection, ensures proper cleanup and
        handles timeouts."""
        self.log.debug(f"opening connection to zookeeper @ {self.hosts}")
        zk = KazooClient(hosts=",".join(self.hosts))
        zk.start()
        try:
            yield zk
        finally:
            self.log.debug(f"closing connection to zookeeper @ {self.hosts}")
            zk.stop()
            zk.close()

    def __init__(self, hosts: list[str], rootdir: Path | str):
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
        super().__init__(rootdir=rootdir)

    # crud functions
    def create(self, path: Path | str, data: bytes) -> None:
        if self.path_exists(str(path)):
            raise NotEmptyError(f"Path {path} already exists.")
        with self._get_zk_client() as zk:
            zk.create(str(path), data, makepath=True)

    def read(self, path: Path | str) -> bytes:
        with self._get_zk_client() as zk:
            data = None
            try:
                data, stat = zk.get(str(path))
                # Save stat to check if the path was altered when we try an update later.
                self._path_versions[str(path)] = stat
                return data
            except NoNodeError:
                raise PathNotFoundError(f"Path: {path} does not exist.")
            self._path_versions[str(path)] = stat
            if data is None:
                return b""

    def update(self, path: Path | str, data: bytes, force: bool = False) -> None:
        with self._get_zk_client() as zk:
            version = -1 if force else self._path_versions[str(path)]
            try:
                zk.set(str(path), data, version=version)
            except ZKBadVersionError:
                raise BadVersionError(f"Content at {path} has been updated by "
                                      f"another entity since reading.")

    def delete(self, path: Path | str, recursive: bool = False) -> None:
        with self._get_zk_client() as zk:
            try:
                zk.delete(str(path), recursive=recursive)
            except ZKNotEmptyError:
                raise NotEmptyError(f"Failed to delete. Node contains children: {path}")
            except NoNodeError:
                raise PathNotFoundError(f"Failed to delete. Path {path} is invalid.")

    # utility
    def exists(self, path: Path | str) -> bool:
        with self._get_zk_client() as zk:
            return zk.exists(str(path))

    def list_files(self, path: Path | str) -> list[str]:
        with self._get_zk_client() as zk:
            children: list = zk.get_children(str(path))
            if len(children) == 0:
                raise ValueError(f"Cannot list files on a file: {path}")
            return children


def setup_scopes():
    """
    Ensures scopes defined in settings file exist in zookeeper, creates if they don't exist.
    """
    logger.info("Ensuring scopes exist in zookeeper")
    with get_zk_client() as zk:
        zk.ensure_path(f"/{settings.zk_root_node}/defaults")
        for scope in settings.scopes:
            if zk.ensure_path(f"/{settings.zk_root_node}/{scope.name}"):
                logger.info(f"Scope '{scope.name}' in zookeeper")


async def kazoo_timeout_handler(request: Request, exc: KazooTimeoutError):
    return JSONResponse(
        status_code=503, content={"message": "Zookeeper connection timed out, service unavailable"}
    )
