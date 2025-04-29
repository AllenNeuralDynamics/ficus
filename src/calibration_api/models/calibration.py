import datetime 

from pydantic import BaseModel
from typing import Any, Optional


class Calibration(BaseModel):
    device_name: str
    input: Any
    output: Any
    date: Optional[datetime.datetime]
    description: Optional[str]
    notes: Optional[str]

class CalibrationDB(Calibration):
    id: int
    rig_name: str
