from kazoo.client import KazooClient


def get_zk_client():
    # zk = KazooClient(hosts="127.0.0.1:2181")
    zk = KazooClient(hosts="eng-logtools:2181")
    zk.start()
    try:
        yield zk
    finally:
        zk.stop()
        zk.close()
