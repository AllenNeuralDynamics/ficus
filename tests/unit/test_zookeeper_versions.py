from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from ficus.database import zookeeper


def test_update_uses_integer_version_from_read_and_tracks_next_version(monkeypatch):
    zk = SimpleNamespace(
        get=Mock(return_value=(b"old", SimpleNamespace(version=3))),
        set=Mock(side_effect=[SimpleNamespace(version=4), SimpleNamespace(version=5)]),
    )
    monkeypatch.setattr(zookeeper, "ZKClientContextManager", lambda _hosts: nullcontext(zk))
    store = zookeeper.ZKStore.__new__(zookeeper.ZKStore)
    store.rootdir = Path("/ficus")
    store.hosts = []
    store._path_versions = {}

    assert store.read("config.yml") == b"old"
    store.update("config.yml", b"first")
    store.update("config.yml", b"second")

    assert zk.set.call_args_list[0].kwargs["version"] == 3
    assert zk.set.call_args_list[1].kwargs["version"] == 4
