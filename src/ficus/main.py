import sys

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from kazoo.handlers.threading import KazooTimeoutError
from loguru import logger
from typing import Any, Dict

from ficus.database.data_store import DataStore
from ficus.database.zookeeper import kazoo_timeout_handler
from ficus.routers import router

from ficus.database.zookeeper import ZKStore
from ficus.database.filesys import FileSysStore

from ficus.core.config import settings, Settings as FicusSettings
from ficus.core.proxy import ForwardedPrefixMiddleware
from ficus.routers.utils import data_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level)
    logger.info("Starting Ficus API...")
    logger.info("Connecting to DataStore")
    app.state.settings = settings
    if settings.store == 'zookeeper':
        app.state.data_store = ZKStore(hosts=settings.zk_hosts,
                                     rootdir=settings.root_dir,
                                     scopes=settings.scopes,
                                     timeout=settings.zk_timeout)
    elif settings.store == "file_system":
        app.state.data_store = FileSysStore(rootdir=settings.root_dir,
                                            scopes=settings.scopes)

    yield
    logger.info("Shutting down Ficus API...")


app = FastAPI(
    root_path=settings.root_path, docs_url="/docs", openapi_url="/openapi.json", lifespan=lifespan
)
if not settings.root_path:
    app.add_middleware(ForwardedPrefixMiddleware)



app.include_router(router)
app.add_exception_handler(KazooTimeoutError, kazoo_timeout_handler)


@app.get("/", tags=["Health"])
def health_check() -> Dict[str, Any]:
    """Health check."""
    return {"message": "Hello"}
