from pydantic import BaseModel, Field, StringConstraints
from typing import Annotated

from calibration_api.database.schemas.partial import partial_model


class RigAddUpdate(BaseModel):
    rig_name: Annotated[str, StringConstraints(to_lower=True, pattern=r"^[a-zA-Z0-9]+_[a-zA-Z0-9]+_[a-zA-Z0-9]+$")] = (
        Field(examples=["frg_1_test"])
    )
    hostname: Annotated[str, StringConstraints(to_lower=True)] = Field(examples=["W10TEST"])


class Rig(RigAddUpdate):
    rig_type: str
    comp_type: str
    instance: str


PartialRigAddUpdate = partial_model(RigAddUpdate)
