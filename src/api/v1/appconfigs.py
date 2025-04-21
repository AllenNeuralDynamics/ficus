from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, Literal
import traceback

from src.api.v1.mpeconfig import source_configuration


router = APIRouter(prefix="/appconfigs", tags=["Application Configs"])


@router.get("/")
def get_config(
    app_name: str | None = None,
    rig_id: str | None = None,
    comp_id: str | None = None,
    version: str | None = None,
    config_type: Literal["configuration", "logging"] = "configuration",
) -> Dict[str, Any]:
    try:
        return source_configuration(app_name, rig_id=rig_id, comp_id=comp_id, version=version, config_type=config_type)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=traceback.format_exc(),
        )
