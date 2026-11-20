#from contextlib import contextmanager

from kazoo.client import KazooClient, KazooState
from kazoo.handlers.threading import KazooTimeoutError
from kazoo.exceptions import ConnectionLoss, OperationTimeoutError, SessionExpiredError
from kazoo.exceptions import NotEmptyError as ZKNotEmptyError
from kazoo.retry import KazooRetry, RetryFailedError
from kazoo.exceptions import BadVersionError as ZKBadVersionError
from ficus.core.exceptions import (
    BadVersionError,
    PathIsDirectoryError,
    PathNotFoundError,
    StoreUnavailableError,
)
from kazoo.recipe.watchers import NoNodeError
from loguru import logger
from pathlib import Path
from threading import Event, Lock

from ficus.database.data_store import DataStore

# ZooKeeper unreachable or the connection dropped mid-request: raised as StoreUnavailableError.
ZK_UNAVAILABLE_ERRORS = (
    KazooTimeoutError,
    ConnectionLoss,
    SessionExpiredError,
    OperationTimeoutError,
    RetryFailedError,
)

# Reads retry through a brief disconnect
READ_RETRY = KazooRetry(max_tries=3, delay=0.1, backoff=2, max_delay=1.0)

class ZKConnection:
    """One ZooKeeper connection shared by every call on a store, opened on first use.

    Kazoo reconnects by itself if the link drops. ``with connection as zk`` hands out the shared
    client; leaving the block doesn't close it, ``close()`` does (on shutdown).
    """

    def __init__(self, hosts: list[str], timeout: float = 15.0):
        self._lock: Lock = Lock()
        self.hosts: list[str] = hosts
        self.timeout: float = timeout  # seconds to wait for the connection
        self._zk: KazooClient | None = None
        self._connected: Event = Event()  # follows the client's state

    def __enter__(self) -> KazooClient:
        with self._lock:
            if self._zk is None:
                zk = KazooClient(hosts=",".join(self.hosts))
                zk.add_listener(self._on_state)
                try:
                    zk.start(timeout=self.timeout)
                except KazooTimeoutError as error:  # the next call tries again
                    raise StoreUnavailableError(
                        "Zookeeper connection timed out, service unavailable"
                    ) from error
                self._connected.set()
                self._zk = zk
            return self._zk

    def _on_state(self, state: KazooState) -> None:
        # Called from kazoo's thread on every change: CONNECTED, SUSPENDED, LOST.
        if state == KazooState.CONNECTED:
            self._connected.set()
        else:
            self._connected.clear()

    def ensure_connected(self) -> None:
        """Wait up to ``timeout`` for the connection; ``StoreUnavailableError`` if it stays down.

        Kazoo queues a command sent while it's reconnecting and waits for it with no limit, so
        without this a request would hang until ZooKeeper is back.
        """
        if not self._connected.wait(self.timeout):
            raise StoreUnavailableError("Zookeeper connection lost, service unavailable")

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Return False to let exceptions propagate normally
        return False

    def close(self) -> None:
        with self._lock:
            if self._zk is not None:
                self._zk.stop()
                self._zk.close()
                self._zk = None


class ZKStore(DataStore):
    """CRUD functions for Zookeeper-based data store."""

    def __init__(self, hosts: list[str], rootdir: Path | str, scopes: set[str],
                 create_missing_scopes: bool = True, timeout: float = 15.0):
        """
        Parameters
        ----------
        hosts:
            list of hosts. ex: `["127.0.0.1:8000", "127.0.0.1:9000"]`
        timeout:
            seconds to wait for a connection before raising ``KazooTimeoutError``.
        """
        self.log = logger.bind(custom_name=self.__class__.__name__)
        self.hosts = hosts
        self.timeout = timeout
        self._connection = ZKConnection(hosts, timeout)
        self._path_versions = {}  # dict of all file reads to track versions
                                  # when calling update() on the same path.
        super().__init__(rootdir=rootdir, scopes=scopes,
                         create_missing_scopes=create_missing_scopes)

    def close(self) -> None:
        self._connection.close()

    def _read(self, func, *args, **kwargs):
        """Call a read-only or idempotent ZooKeeper command, retrying a brief disconnect."""
        def attempt():
            self._connection.ensure_connected()
            return func(*args, **kwargs)

        try:
            # A copy per call: a KazooRetry counts its attempts, so one can't be shared by threads.
            return READ_RETRY.copy()(attempt)
        except ZK_UNAVAILABLE_ERRORS as error:
            raise StoreUnavailableError("Zookeeper connection lost, service unavailable") from error

    def _write(self, func, *args, **kwargs):
        """Call a ZooKeeper command that changes data: once, no retry."""
        self._connection.ensure_connected()
        try:
            return func(*args, **kwargs)
        except ZK_UNAVAILABLE_ERRORS as error:
            raise StoreUnavailableError("Zookeeper connection lost, service unavailable") from error

    # crud functions
    def create(self, path: Path | str, data: bytes | None) -> None:
        path = self._sanitize(path)
        with self._connection as zk:
            if self.exists(path) and self.is_file(path):
                raise FileExistsError(f"Path {path} already exists.")
            if data is None:  # assume path is folder.
                self._read(zk.ensure_path, path.as_posix())
                return
            self._write(zk.create, path.as_posix(), data, makepath=True)

    def read(self, path: Path | str) -> bytes:
        path = self._sanitize(path)
        with self._connection as zk:
            data = None
            try:
                data, stat = self._read(zk.get, path.as_posix())
                # Save stat to check if the path was altered when we try an update later.
                self._path_versions[path.as_posix()] = stat.version
                return data
            except NoNodeError:
                raise PathNotFoundError(f"Path: {path} does not exist.")

    def update(self, path: Path | str, data: bytes, force: bool = False) -> None:
        path = self._sanitize(path)
        with self._connection as zk:
            # force if specified, or if we've never read the data in the first place.
            version = -1 if force else self._path_versions.get(path.as_posix(), -1)
            try:
                stat = self._write(zk.set, path.as_posix(), data, version=version)
                self._path_versions[path.as_posix()] = stat.version
            except ZKBadVersionError:
                raise BadVersionError(f"Content at {path} has been updated by "
                                      f"another entity since reading.")

    def delete(self, path: Path | str, recursive: bool = False) -> None:
        path = self._sanitize(path)
        with self._connection as zk:
            try:
                self._write(zk.delete, path.as_posix(), recursive=recursive)
            except ZKNotEmptyError:
                raise PathIsDirectoryError(f"Failed to delete. Node contains children: {path}")
            except NoNodeError:
                raise PathNotFoundError(f"Failed to delete. Path {path} is invalid.")

    # utility
    def exists(self, path: Path | str) -> bool:
        path = self._sanitize(path)
        with self._connection as zk:
            exists = self._read(zk.exists, path.as_posix())
            return exists
            #return zk.exists(path.as_posix())

    def is_file(self, path: Path | str) -> bool:
        path = self._sanitize(path)
        with self._connection as zk:
            data, _ = self._read(zk.get, path.as_posix())
            children: list = self._read(zk.get_children, path.as_posix())
            is_file = len(children) == 0 and len(data) > 0
            return is_file

    def list_files(self, path: Path | str) -> list[str]:
        path = self._sanitize(path)
        if not self.exists(path):
            raise FileNotFoundError(f"Path {path} does not exist.")
        with self._connection as zk:
            if self.is_file(path):
                raise ValueError(f"Cannot list files on a file: {path}")
            children: list = self._read(zk.get_children, path.as_posix())
            files = [child for child in children if self.is_file(path / child)]
            return files

    def list_directories(self, path: Path | str) -> list[str]:
        path = self._sanitize(path)
        if not self.exists(path):
            raise FileNotFoundError(f"Path {path} does not exist.")
        with self._connection as zk:
            children = self._read(zk.get_children, path.as_posix())
            return [child for child in children if not self.is_file(path / child)]
