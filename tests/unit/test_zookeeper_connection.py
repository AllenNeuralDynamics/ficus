from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from kazoo.client import KazooState
from kazoo.exceptions import ConnectionLoss
from kazoo.handlers.threading import KazooTimeoutError
from kazoo.retry import KazooRetry, RetryFailedError

from ficus import main
from ficus.database import zookeeper
from tests.zk_data import StubConnection
from ficus.core.exceptions import StoreUnavailableError
from ficus.services.configs import get_config


class CountingClient:
    """Stands in for KazooClient and records how it's used."""

    made: list["CountingClient"] = []
    fail_starts = 0

    def __init__(self, hosts):
        self.hosts = hosts
        self.started = self.closed = False
        self.listeners = []
        CountingClient.made.append(self)

    def add_listener(self, listener):
        self.listeners.append(listener)

    def change_state(self, state):
        for listener in self.listeners:
            listener(state)

    def start(self, timeout):
        if CountingClient.fail_starts:
            CountingClient.fail_starts -= 1
            raise KazooTimeoutError("unreachable")
        self.started = True

    def stop(self):
        self.started = False

    def close(self):
        self.closed = True


@pytest.fixture
def counting(monkeypatch):
    CountingClient.made = []
    CountingClient.fail_starts = 0
    monkeypatch.setattr(zookeeper, "KazooClient", CountingClient)
    return CountingClient


def test_connection_opens_once_and_is_shared(counting):
    connection = zookeeper.ZKConnection(["zk1:2181", "zk2:2181"], timeout=2)
    with connection as first:
        with connection as nested:
            assert nested is first
    with connection as later:
        assert later is first
    assert len(counting.made) == 1
    assert first.hosts == "zk1:2181,zk2:2181" and first.started


def test_a_failed_connect_is_retried_on_the_next_call(counting):
    counting.fail_starts = 1
    connection = zookeeper.ZKConnection(["zk1:2181"])
    with pytest.raises(StoreUnavailableError, match="timed out"):
        with connection:
            pass
    with connection as zk:
        assert zk.started
    assert len(counting.made) == 2


def test_close_stops_the_client_and_the_next_call_reconnects(counting):
    connection = zookeeper.ZKConnection(["zk1:2181"])
    with connection as zk:
        pass
    connection.close()
    assert zk.closed and not zk.started
    connection.close()  # closing twice is fine
    with connection as again:
        assert again is not zk


def test_a_dropped_connection_fails_fast_instead_of_hanging(counting):
    """Kazoo would queue the command until ZooKeeper is back; we give up after the timeout."""
    connection = zookeeper.ZKConnection(["zk1:2181"], timeout=0.05)
    with connection as zk:
        connection.ensure_connected()
    zk.change_state(KazooState.SUSPENDED)
    with pytest.raises(StoreUnavailableError, match="lost"):
        connection.ensure_connected()
    zk.change_state(KazooState.CONNECTED)
    connection.ensure_connected()  # back: commands go through again
    assert len(counting.made) == 1  # the same client reconnected


def test_store_commands_wait_for_the_connection(counting):
    """Reads and writes both check the connection first, so neither hangs during an outage."""
    store = zookeeper.ZKStore.__new__(zookeeper.ZKStore)
    store.rootdir = Path("/ficus")
    store._path_versions = {}
    store._connection = zookeeper.ZKConnection(["zk1:2181"], timeout=0.05)
    with store._connection as zk:
        pass
    zk.change_state(KazooState.LOST)
    with pytest.raises(StoreUnavailableError):
        store._read(lambda: "unreachable")
    with pytest.raises(StoreUnavailableError):
        store._write(lambda: "unreachable")


def test_a_whole_config_resolution_uses_one_connection(zookeeper_store, monkeypatch):
    """Before, every exists/is_file/read call opened (and closed) its own connection."""
    made = []
    fake = zookeeper.KazooClient  # conftest's FakeZK factory

    def recording(hosts):
        made.append(hosts)
        return fake(hosts)

    monkeypatch.setattr(zookeeper, "KazooClient", recording)
    zookeeper_store.close()
    get_config(zookeeper_store, "software_a", scope_identifiers={"hostname": "w11dt000001"})
    get_config(zookeeper_store, "software_a", scope_identifiers={"subject_id": "614173"})
    assert len(made) == 1


class FlakyZK:
    """A client whose commands raise ConnectionLoss the first ``failures`` times."""

    def __init__(self, failures):
        self.failures = failures
        self.calls = []

    def _maybe_fail(self, name):
        self.calls.append(name)
        if self.failures:
            self.failures -= 1
            raise ConnectionLoss()

    def get(self, path):
        self._maybe_fail("get")
        return b"data", SimpleNamespace(version=1)

    def set(self, path, data, version=-1):
        self._maybe_fail("set")
        return SimpleNamespace(version=2)


def _store(zk):
    store = zookeeper.ZKStore.__new__(zookeeper.ZKStore)
    store.rootdir = Path("/ficus")
    store._connection = StubConnection(zk)
    store._path_versions = {}
    return store


@pytest.fixture
def no_retry_sleep(monkeypatch):
    monkeypatch.setattr(
        zookeeper, "READ_RETRY", KazooRetry(max_tries=3, sleep_func=lambda _: None)
    )


def test_a_read_retries_through_a_brief_disconnect(no_retry_sleep):
    zk = FlakyZK(failures=2)
    assert _store(zk).read("config.yml") == b"data"
    assert zk.calls == ["get", "get", "get"]


def test_a_read_gives_up_after_the_retries(no_retry_sleep):
    zk = FlakyZK(failures=10)
    with pytest.raises(StoreUnavailableError) as raised:
        _store(zk).read("config.yml")
    assert isinstance(raised.value.__cause__, RetryFailedError)
    assert len(zk.calls) == 4  # the first try and 3 retries


def test_a_write_is_not_retried(no_retry_sleep):
    """A retried set after a lost reply could report a false version conflict."""
    zk = FlakyZK(failures=1)
    with pytest.raises(StoreUnavailableError):
        _store(zk).update("config.yml", b"new", force=True)
    assert zk.calls == ["set"]


@pytest.mark.parametrize(
    "url", ["/v1/configs/software_a?hostname=w11dt000001", "/v1/leaves/software_a"]
)
def test_an_unreachable_store_is_503_not_404(filesys_store, monkeypatch, url):
    """The config routes turn other errors into 404s; an outage must still be a 503."""
    def unavailable(path):
        raise StoreUnavailableError("Zookeeper connection lost, service unavailable")

    monkeypatch.setattr(filesys_store, "read", unavailable)
    monkeypatch.setattr(main.app.state, "data_store", filesys_store, raising=False)
    response = TestClient(main.app).get(url)
    assert response.status_code == 503
    assert response.json() == {"message": "Zookeeper connection lost, service unavailable"}
