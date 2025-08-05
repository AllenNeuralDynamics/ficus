from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from calibration_api.database.rigs_pg_db.models.calibrations import Calibrations
from calibration_api.database.rigs_pg_db.models.rigs import Rigs
from calibration_api.database.rigs_pg_db.schemas.calibration import CalibrationAdd, PartialCalibrationUpdate
import calibration_api.crud.rigs_pg_db.rigs as crud_rigs


def get_calibration(
    db: Session, rig_name: str, device_name: str | None = None, datetime: datetime | None = None
) -> Calibrations:
    """Fetches calibration from the database based on provided filters. Returns a single device calibration."""
    filters = [
        Calibrations.rig_name == rig_name.lower() if rig_name else None,
        Calibrations.device_name == device_name.lower() if device_name else None,
        Calibrations.date >= datetime if datetime else None,
    ]
    calibration = db.query(Calibrations).filter(*[f for f in filters if f is not None]).first()
    if calibration is None:
        raise HTTPException(
            status_code=404,
            detail=f"Calibration for device {device_name} on rig {rig_name} not found",
        )
    return calibration


def get_calibrations(
    db: Session, rig_name: str | None = None, device_name: str | None = None, datetime: datetime | None = None
) -> list[Calibrations]:
    """Fetches calibrations from the database based on provided filters."""
    filters = [
        Calibrations.rig_name == rig_name.lower() if rig_name else None,
        Calibrations.device_name == device_name.lower() if device_name else None,
        Calibrations.date >= datetime if datetime else None,
    ]
    calibrations = db.query(Calibrations).filter(*[f for f in filters if f is not None]).all()
    return calibrations


def create_calibrations(db: Session, rig_name: str, calibrations: list[CalibrationAdd]) -> list[Calibrations]:
    """Create new calibrations."""
    # Check if the rig exists in the rigs table
    rig = crud_rigs.get_rig_by_name(db, rig_name)
    if rig is None:
        raise HTTPException(
            status_code=404,
            detail=f"Rig with name {rig_name} not found in rigs table",
        )
    # Proceed to add calibrations
    try:
        calibrations_added = []
        for calibration in calibrations:
            calibration_dict = calibration.model_dump()
            calibration_dict["rig_name"] = rig_name.lower()
            calibration_to_add = Calibrations(**calibration_dict)
            db.add(calibration_to_add)
            calibrations_added.append(calibration_to_add)
        db.commit()
        return calibrations_added
    except IntegrityError as e:
        if e.orig and hasattr(e.orig, "pgcode") and e.orig.pgcode == "23505":  # Unique column violation
            raise HTTPException(
                status_code=409,
                detail=f"Calibration with the same name already exists for that rig (pgcode: {e.orig.pgcode})",
            )
        elif e.orig and hasattr(e.orig, "pgcode"):
            raise HTTPException(
                status_code=404,
                detail=f"Error writing to database (pgcode: {e.orig.pgcode})",
            )
        else:
            raise HTTPException(
                status_code=404,
                detail="Error writing to database (no pgcode available)",
            )


def update_calibration(
    db: Session,
    rig_name: str,
    device_name: str,
    calibration_updates: PartialCalibrationUpdate,  # type: ignore
) -> Calibrations:
    """Updates a calibration in a rig."""
    calibration_to_update = (
        db.query(Calibrations)
        .filter(Calibrations.rig_name == rig_name.lower(), Calibrations.device_name == device_name.lower())
        .first()
    )
    if calibration_to_update is None:
        raise HTTPException(
            status_code=404,
            detail=f"Calibration for device {device_name} on rig {rig_name} not found",
        )

    for name in calibration_updates.model_fields.keys():  # type: ignore
        value = getattr(calibration_updates, name)
        # Check if new rig name exists in rigs table
        if name == "rig_name" and value:
            rig = db.query(Rigs).filter(Rigs.rig_name == value.lower()).first()
            if rig is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Rig with name {value} not found in rigs table. Can't update calibration to be in that rig.",
                )
        # Update calibration fields if new value was given
        if value:
            calibration_to_update.__setattr__(name, value)
    db.commit()

    return calibration_to_update


def delete_calibration(db: Session, rig_name: str, device_name: str) -> Calibrations:
    """Delete a calibration in a rig"""
    calibration_to_delete = (
        db.query(Calibrations)
        .filter(Calibrations.rig_name == rig_name.lower(), Calibrations.device_name == device_name.lower())
        .first()
    )

    if calibration_to_delete is None:
        raise HTTPException(
            status_code=404,
            detail=f"Calibration with device name {device_name} does not exist in {rig_name}",
        )
    db.delete(calibration_to_delete)
    db.commit()
    return calibration_to_delete
