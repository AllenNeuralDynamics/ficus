from fastapi import FastAPI
from typing import Any, Dict

from ficus.api import router


app = FastAPI(root_path="/ficus", docs_url="/docs", openapi_url="/openapi.json")


app.include_router(router)


@app.get("/")
def health_check() -> Dict[str, Any]:
    """Health check."""
    return {"message": "Hello"}
