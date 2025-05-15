from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from typing import Any, Dict, List, Optional

from calibration_api.crud.rigs import (
    create_rigs,
    get_rigs,
    get_rig_by_name,
    update_rig,
    delete_rig_by_name
)
from calibration_api.database.session import get_db
from calibration_api.database.schemas.calibration import Calibration
from calibration_api.database.schemas.rig import RigInput, PartialRigInput


router = APIRouter(prefix="/rigs", tags=["Rigs"])


@router.get("/")
def rigs(
    rig_type: str | None = None,
    instance: str | None = None,
    comp_type: str | None = None,
    hostname: str | None = None,
    db=Depends(get_db)) -> Dict[str, Any]:
    """Get all rigs from the database."""
    rigs = get_rigs(db, rig_type, instance, comp_type, hostname)
    return {
        "message": "Query successful",
        "output": f"{rigs}"
    }


@router.post("/")
def rigs_create(rig_inputs: List[RigInput], db=Depends(get_db)) -> Dict[str, Any]:
    """Add rig to database."""
    try:
        rig = create_rigs(db, rig_inputs)
        return {
            "message": "Added rig",
            "output": f"{rig}"
        }
    except IntegrityError as e:
        raise HTTPException(
            status_code=409,
            detail=f"Rig with the same name already exists: {e}",
        )


@router.get("/{rig_name}")
def rig(rig_name: str, db=Depends(get_db)) -> Dict[str, Any]: 
    """Get specific rig given the rig name."""
    rig = get_rig_by_name(db, rig_name)
    return {
        "message": "Query successful",
        "output": f"{rig}"
    }


@router.patch("/{rig_name}")
def rig_update(rig_name: str, rig_updates: PartialRigInput, db=Depends(get_db)) -> Dict[str, Any]: # type: ignore
    """Get specific rig given the rig name."""
    rig = update_rig(db, rig_name, rig_updates)
    return {
        "message": "Query successful",
        "output": f"{rig}"
    }


# Maybe hide this endpoint until authentication is added
@router.delete("/{rig_name}")
def rig_delete(rig_name: str, db=Depends(get_db)) -> Dict[str, Any]: 
    """Delete specific rig given the rig name."""
    rig = delete_rig_by_name(db, rig_name)
    return {
        "message": "Deleted rig",
        "output": f"{rig}"
    }


# TODO: Should the following two endpoints be in calibrations?

@router.get("/{rig_name}/calibrations")
def get_calibrations_for_rig(rig_name: str, device_name: Optional[str] = None) -> Dict[str, Any]:
    """Get calibrations for a specific rig."""
    # TODO: Implement
    return {
        "message": "Get all calibrations for a rig",
        "input": f"{rig_name} {device_name}"
    }


@router.post("/{rig_name}/calibrations")
def add_calibrations_for_rig(rig_name: str, calibrations: List[Calibration]) -> Dict[str, Any]:
    """Add calibrations""" 
    # TODO: Implement
    # check rig exists in db
    # check calibration doesn't already exists
    # add calibration to rig
    return {
        "message": "Add calibrations to rig",
        "inputs": f"{rig_name} {calibrations[0].model_dump()}"
    }
