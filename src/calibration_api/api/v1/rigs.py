from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from typing import Any

import calibration_api.crud.calibrations as crud_calibrations
import calibration_api.crud.rigs as crud_rigs
from calibration_api.database.session import get_db
from calibration_api.database.schemas.calibration import CalibrationAdd, PartialCalibrationUpdate
from calibration_api.database.schemas.rig import RigAddUpdate, PartialRigAddUpdate


router = APIRouter(prefix="/rigs", tags=["Rigs"])


@router.get("/")
def get_rigs(
    rig_type: str | None = None,
    instance: str | None = None,
    comp_type: str | None = None,
    hostname: str | None = None,
    db: Any = Depends(get_db),
) -> dict[str, Any]:
    """Get all rigs from the database."""
    rigs = crud_rigs.get_rigs(db, rig_type, instance, comp_type, hostname)
    rigs = [rig.to_dict() for rig in rigs]  
    return {"message": "Query successful", "output": rigs}


@router.post("/")
def add_rigs(rig_inputs: list[RigAddUpdate], db: Any = Depends(get_db)) -> dict[str, Any]:
    """Add rig to database."""
    try:
        rigs = crud_rigs.create_rigs(db, rig_inputs)
        rigs = [rig.to_dict() for rig in rigs]  
        return {"message": "Added rig", "output": f"{rigs}"}
    except IntegrityError as e:
        raise HTTPException(
            status_code=409,
            detail=f"Rig with the same name already exists: {e}",
        )


@router.get("/{rig_name}/")
def get_rig(rig_name: str, db: Any = Depends(get_db)) -> dict[str, Any]:
    """Get specific rig given the rig name."""
    try:
        rig = crud_rigs.get_rig_by_name(db, rig_name)
    except HTTPException as e:
        raise e
    return {"message": "Query successful", "output": rig.to_dict()}


@router.patch("/{rig_name}/")
def update_rig(rig_name: str, rig_updates: PartialRigAddUpdate, db: Any = Depends(get_db)) -> dict[str, Any]:  # type: ignore
    """Update specific rig given the rig name."""
    try:
        rig = crud_rigs.update_rig(db, rig_name, rig_updates)
    except HTTPException as e:
        raise e
    return {"message": "Query successful", "output": rig.to_dict()}


# Maybe hide this endpoint until authentication is added
@router.delete("/{rig_name}/")
def delete_rig(rig_name: str, db: Any = Depends(get_db)) -> dict[str, Any]:
    """Delete specific rig given the rig name."""
    try:
        rig = crud_rigs.delete_rig_by_name(db, rig_name)
    except HTTPException as e:
        raise e
    return {"message": "Deleted rig", "output": rig.to_dict()}


################################################################################
#
#   Calibration Endpoints
#
################################################################################


@router.get("/{rig_name}/calibrations/")
def get_calibrations_by_rig(
    rig_name: str, device_name: str | None = None, date: datetime | None = None, db: Any = Depends(get_db)
) -> dict[str, Any]:
    """Get calibrations for a specific rig."""
    calibrations = crud_calibrations.get_calibrations(db, rig_name, device_name, date)
    calibrations = [calibration.to_dict() for calibration in calibrations]  
    return {"message": "Query successful", "input": calibrations}


@router.post("/{rig_name}/calibrations/")
def create_calibrations(
    rig_name: str, calibration_inputs: list[CalibrationAdd], db: Any = Depends(get_db)
) -> dict[str, Any]:
    """Add calibrations."""
    try:
        calibrations = crud_calibrations.create_calibrations(db, rig_name, calibration_inputs)
        calibrations = [calibration.to_dict() for calibration in calibrations]  
    except HTTPException as e:
        raise e
    return {"message": "Added calibrations", "inputs": calibrations}


@router.patch("/{rig_name}/calibrations/{device_name}/")
def update_calibration(
    rig_name: str,
    device_name: str,
    calibration_updates: PartialCalibrationUpdate,  # type: ignore
    db: Any = Depends(get_db),
) -> dict[str, Any]:
    """Update calibration for a device given the rig its on and the device name."""
    try:
        calibration = crud_calibrations.update_calibration(db, rig_name, device_name, calibration_updates)
    except HTTPException as e:
        raise e
    return {"message": "Query successful", "output": calibration.to_dict()}


# Maybe hide this endpoint until authentication is added
@router.delete("/{rig_name}/calibrations/{device_name}/")
def delete_calibration(rig_name: str, device_name: str, db: Any = Depends(get_db)) -> dict[str, Any]:
    """Delete calibration given the rig its on and the device name."""
    try:
        calibration = crud_calibrations.delete_calibration(db, rig_name, device_name)
    except HTTPException as e:
        raise e
    return {"message": "Deleted rig", "output": calibration.to_dict()}
