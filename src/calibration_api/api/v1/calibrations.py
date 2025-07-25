from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from typing import Any


import calibration_api.crud.calibrations as crud_calibrations
from calibration_api.database.schemas.calibration import CalibrationAdd, PartialCalibrationUpdate
from calibration_api.database.session import get_db


router = APIRouter(prefix="/calibrations", tags=["Calibrations"])


@router.get("/")
def get_calibrations(
    rig_name: str | None = None,
    device_name: str | None = None,
    datetime: datetime | None = None,
    db: Any = Depends(get_db),
) -> dict[str, Any]:
    """Get all calibrations"""
    calibrations = crud_calibrations.get_calibrations(db, rig_name, device_name, datetime)
    calibrations = [calibration.to_dict() for calibration in calibrations]   
    return {"message": "Query successful", "inputs": calibrations}


@router.get("/{device_name}")
def get_calibration(
    rig_name: str, device_name: str, datetime: datetime | None = None, db: Any = Depends(get_db)
) -> dict[str, Any]:
    """Get a specific calibration for a device given the rig name and device name."""
    try:
        calibration = crud_calibrations.get_calibration(db, rig_name, device_name, datetime)
    except HTTPException as e:
        raise e
    return {"message": "Query successful", "inputs": calibration.to_dict()}


@router.post("/")
def add_calibrations(
    rig_name: str, calibration_inputs: list[CalibrationAdd], db: Any = Depends(get_db)
) -> dict[str, Any]:
    """Add calibration(s) to a rig."""
    try:
        calibrations = crud_calibrations.create_calibrations(db, rig_name, calibration_inputs)
        calibrations = [calibration.to_dict() for calibration in calibrations]   
        return {"message": "Added calibrations", "inputs": calibrations}
    except HTTPException as e:
        raise e


@router.patch("/{device_name}/")
def update_calibration(
    rig_name: str,
    device_name: str,
    calibration_updates: PartialCalibrationUpdate,  # type: ignore
    db: Any = Depends(get_db),
) -> dict[str, Any]:
    """Update calibration for a device given the rig name and device name."""
    try:
        calibration = crud_calibrations.update_calibration(db, rig_name, device_name, calibration_updates)
        return {"message": "Updated calibration", "inputs": calibration.to_dict()}
    except HTTPException as e:
        raise e


# Maybe hide this endpoint until authentication is added
@router.delete("/{device_name}/")
def delete_calibration(rig_name: str, device_name: str, db: Any = Depends(get_db)) -> dict[str, Any]:
    """Delete calibration given the rig its on and the device name."""
    try:
        calibration = crud_calibrations.delete_calibration(db, rig_name, device_name)
    except HTTPException as e:
        raise e
    return {"message": "Deleted rig", "output": calibration.to_dict()}
