from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger
from typing import Any, Dict

from ficus.api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Ficus API...")
    yield
    logger.info("Shutting down Ficus API...")


app = FastAPI(root_path="/ficus", docs_url="/docs", openapi_url="/openapi.json", lifespan=lifespan)


app.include_router(router)


@app.get("/")
def health_check() -> Dict[str, Any]:
    """Health check."""
    return {"message": "Hello"}
