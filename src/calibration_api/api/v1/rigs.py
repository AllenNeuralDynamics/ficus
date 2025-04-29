from fastapi import APIRouter

from typing import Any, Dict, List, Optional

from calibration_api.models.calibration import Calibration
from calibration_api.models.rig import Rig


router = APIRouter(prefix="/rigs", tags=["Rigs"])


@router.get("/")
def get_rigs(
    rig_type: str | None = None,
    comp_type: str | None = None,
    instance: str | None = None,
    host_name: str | None = None) -> Dict[str, Any]:
    """Get all rigs from the database."""
    return {
        "message": "Get all rigs",
        "input": f"{rig_type} {comp_type} {instance} {host_name}"
    }


@router.post("/")
def add_rigs(rig_input: List[Rig]) -> Dict[str, Any]:
    """Add rig to database."""
    return {
        "message": "Add rig",
        "input": f"{rig_input[0].model_dump()}"
    }


@router.get("/{rig_name}")
def get_rig(rig_name: str) -> Dict[str, Any]: 
    """Get specific rig given the rig name."""
    return {
        "message": "Get specific rig",
        "input": f"{rig_name}"
    }


@router.get("/{rig_name}/calibrations")
def get_calibrations_for_rig(rig_name: str, device_name: Optional[str] = None) -> Dict[str, Any]:
    """Get calibrations for a specific rig."""
    return {
        "message": "Get all calibrations for a rig",
        "input": f"{rig_name} {device_name}"
    }


@router.post("/{rig_name}/calibrations")
def add_calibrations_for_rig(rig_name: str, calibrations: List[Calibration]) -> Dict[str, Any]:
    """Add calibrations""" 
    # check rig exists in db
    # check calibration doesn't already exists
    # add calibration to rig
    return {
        "message": "Add calibrations to rig",
        "inputs": f"{rig_name} {calibrations[0].model_dump()}"
    }


# @router.patch("/")
# def add_rig(rig_input: PartialRig) -> Dict[str, Any]:
#     """Add rig to database."""
#     return {"message": "Get all rigs..."}
