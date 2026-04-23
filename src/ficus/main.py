import os

from contextlib import asynccontextmanager
from fastapi import FastAPI
from kazoo.handlers.threading import KazooTimeoutError
from loguru import logger
from typing import Any, Dict

from ficus.database.zookeeper import kazoo_timeout_handler, setup_scopes
from ficus.routers import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Ficus API...")
    yield
    logger.info("Shutting down Ficus API...")


setup_scopes()


app_name = os.getenv("API_NAME", "ficus")
app = FastAPI(
    root_path=f"/{app_name}", docs_url="/docs", openapi_url="/openapi.json", lifespan=lifespan
)


app.include_router(router)
app.add_exception_handler(KazooTimeoutError, kazoo_timeout_handler)


@app.get("/", tags=["Health"])
def health_check() -> Dict[str, Any]:
    """Health check."""
    return {"message": "Hello"}
