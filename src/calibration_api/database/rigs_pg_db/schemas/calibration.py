import datetime

from pydantic import BaseModel, Field, StringConstraints
from typing import Annotated, Any 

from calibration_api.database.rigs_pg_db.schemas.partial import partial_model


class CalibrationAdd(BaseModel):
    device_name: Annotated[str, StringConstraints(to_lower=True)] = Field(examples=["lick_detector"])
    input_data: Any = Field(examples=[{"input": "data"}])
    output_data: Any = Field(examples=[{"input": "data"}])
    date: datetime.datetime = Field(default=datetime.datetime.now(), examples=["1996-08-18T06:00:00Z"])
    description: str | None = Field(default="")
    notes: str | None = Field(default="")


class CalibrationUpdate(CalibrationAdd):
    rig_name: str = Field(examples=["frg_1_a"])


class Calibration(CalibrationUpdate):
    id: int


PartialCalibrationUpdate = partial_model(CalibrationUpdate)
