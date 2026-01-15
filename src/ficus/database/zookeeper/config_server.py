from contextlib import contextmanager
from kazoo.client import KazooClient
from loguru import logger


@contextmanager
def get_zk_client():
    hosts = "127.0.0.1:2181" 
    # hosts = "eng-logtools:2181"

    logger.debug(f"opening connection to zookeeper @ {hosts}") 
    zk = KazooClient(hosts=hosts)
    zk.start()
    try:
        yield zk
    finally:
        logger.debug(f"closing connection to zookeeper @ {hosts}") 
        zk.stop()
        zk.close()
