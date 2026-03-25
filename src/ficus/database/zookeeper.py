import os

from fastapi import Request
from fastapi.responses import JSONResponse
from contextlib import contextmanager
from kazoo.client import KazooClient
from kazoo.handlers.threading import KazooTimeoutError
from loguru import logger


@contextmanager
def get_zk_client():
    hosts = os.getenv("ZK_HOST", "eng-logtools:2181")
    hosts = "eng-logtools:2181"

    logger.debug(f"opening connection to zookeeper @ {hosts}")
    zk = KazooClient(hosts=hosts)
    zk.start()
    try:
        yield zk
    finally:
        logger.debug(f"closing connection to zookeeper @ {hosts}")
        zk.stop()
        zk.close()


async def kazoo_timeout_handler(request: Request, exc: KazooTimeoutError):
    return JSONResponse(status_code=503, content={"message": "Zookeeper connection timed out, service unavailable"})
