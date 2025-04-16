from fastapi import FastAPI
from typing import Any, Dict

from src.api import router


app = FastAPI()

app.include_router(router)


@app.get("/")
def health_check() -> Dict[str, Any]:
    """Health check."""
    return {"message": "Hello"}
