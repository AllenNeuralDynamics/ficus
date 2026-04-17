import os

from fastapi import Request
from fastapi.responses import JSONResponse
from contextlib import contextmanager
from kazoo.client import KazooClient
from kazoo.handlers.threading import KazooTimeoutError
from loguru import logger

from ficus.core.config import settings


def setup_scopes():
    logger.info("Ensuring scopes exist in zookeeper")
    with get_zk_client() as zk:
        zk.ensure_path(f"/{settings.zk_root_node}/defaults")
        for scope in settings.scopes:
            if zk.ensure_path(f"/{settings.zk_root_node}/{scope.name}"):
                logger.info(f"Scope '{scope.name}' in zookeeper")


@contextmanager
def get_zk_client():
    hosts = settings.zk_host

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
