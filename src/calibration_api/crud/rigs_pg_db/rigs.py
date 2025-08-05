from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from calibration_api.database.rigs_pg_db.models.rigs import Rigs
from calibration_api.database.rigs_pg_db.schemas.rig import RigAddUpdate, PartialRigAddUpdate


def get_rigs(
    db: Session,
    rig_type: str | None = None,
    instance: str | None = None,
    comp_type: str | None = None,
    hostname: str | None = None,
) -> list[Rigs]:
    """Fetches rigs from the database based on provided filters."""
    filters = [
        Rigs.rig_type == rig_type.lower() if rig_type else None,
        Rigs.instance == instance.lower() if instance else None,
        Rigs.comp_type == comp_type.lower() if comp_type else None,
        Rigs.hostname == hostname.lower() if hostname else None,
    ]
    rigs = db.query(Rigs).filter(*[f for f in filters if f is not None]).all()
    return rigs


def get_rig_by_name(db: Session, rig_name: str) -> Rigs:
    """Fetches a rig by its specified name."""
    rig = db.query(Rigs).filter(Rigs.rig_name == rig_name.lower()).first()
    if rig is None:
        raise HTTPException(
            status_code=404,
            detail=f"Rig with name {rig_name} not found",
        )
    return rig


def create_rigs(db: Session, rig_inputs: list[RigAddUpdate]) -> list[Rigs]:
    """Create a new rig."""
    try:
        rigs_added = []
        for rig in rig_inputs:
            rig_dict = rig.model_dump()
            rig_full_name_list = rig_dict["rig_name"].split("_")
            rig_dict["rig_type"] = rig_full_name_list[0]
            rig_dict["instance"] = rig_full_name_list[1]
            rig_dict["comp_type"] = rig_full_name_list[2]

            rig_to_add = Rigs(**rig_dict)
            db.add(rig_to_add)
            rigs_added.append(rig_to_add)
        db.commit()
        return rigs_added
    except IntegrityError as e:
        if e.orig and hasattr(e.orig, "pgcode") and e.orig.pgcode == "23505":  # Unique column violation
            raise HTTPException(
                status_code=409,
                detail=f"Rig with the same name already exists (pgcode: {e.orig.pgcode})",
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


def update_rig(db: Session, rig_name: str, rig_updates: PartialRigAddUpdate) -> Rigs:  # type: ignore
    """Updates the hostname for a rig."""
    rig_to_update = db.query(Rigs).filter(Rigs.rig_name == rig_name.lower()).first()
    if rig_to_update is None:
        raise HTTPException(
            status_code=404,
            detail=f"Rig with name {rig_name} not found",
        )
    if rig_updates.hostname:  # type: ignore
        rig_to_update.hostname = rig_updates.hostname  # type: ignore
    try: 
        if rig_updates.rig_name:  # type: ignore
            rig_to_update.rig_name = rig_updates.rig_name  # type: ignore
            rig_full_name_list = rig_to_update.rig_name.split("_")
            rig_to_update.rig_type = rig_full_name_list[0]
            rig_to_update.instance = rig_full_name_list[1]
            rig_to_update.comp_type = rig_full_name_list[2]
        db.commit()
    except IntegrityError as e:
        if e.orig and hasattr(e.orig, "pgcode") and e.orig.pgcode == "23505":  # Unique column violation
            raise HTTPException(
                status_code=409,
                detail=f"Rig with the same name already exists (pgcode: {e.orig.pgcode})",
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

    return rig_to_update


def delete_rig_by_name(db: Session, rig_name: str) -> Rigs:
    """Delete a rig by its name."""
    rig_to_delete = db.query(Rigs).filter(Rigs.rig_name == rig_name.lower()).first()
    if rig_to_delete is None:
        raise HTTPException(
            status_code=404,
            detail=f"Rig with name {rig_name} not found",
        )
    db.delete(rig_to_delete)
    db.commit()
    return rig_to_delete
