from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, Literal
import traceback

from src.api.v1.mpeconfig import source_configuration
from src.utils.rig_parser import parse_rig_name


router = APIRouter(prefix="/appconfigs", tags=["Application Configs"])


@router.get("/")
def get_config(
    app: str | None = None,
    rig: str | None = None,
    version: str | None = None,
    config_type: str = "configuration",
) -> Dict[str, Any]:
    """Get application configuration.

    Access pattern is conserved from mpetk/mpeconfig, using zookeeper as a backend.
    Config defaults will always be returned, even if the app has no specific config.
    Zookeeper is structured with global defaults, project defaults, and rig-specific overrides.
    These three levels get merged to form the final configuration.

    Args:
        app (str): Application/project name, e.g. "waterlog", "mouse_director"
        rig (str): Rig name, e.g. "MESO.1-Acq", "WL.2"
        version (str): Application version. Currently configs are not versioned so this is unused
        config_type (str): Type of configuration to retrieve, currently either "configuration" or "logging_v2"
    Returns:
        Dict[str, Any]: Configuration dictionary.

    Examples: 
        >>> config = get_config('waterlog', 'WL.2')
        >>> log_config = get_config('waterlog', 'WL.2', config_type='logging_v2')
    """
    try:
        rig_type, instance, comp_type = parse_rig_name(rig)

        return source_configuration(
            app,
            rig_id=f"{rig_type}.{instance}" if instance else rig_type,
            comp_id=rig,
            version=version,
            config_type=config_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=traceback.format_exc(),
        )
