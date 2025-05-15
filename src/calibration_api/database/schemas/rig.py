from pydantic import BaseModel, Field, StringConstraints
from typing import Annotated

from calibration_api.database.schemas.partial import partial_model

# TODO: Add constraints 
#   - hostname
#   - rig_type
#   - comp_type
#   - instance

class RigInput(BaseModel): 
    rig_name: Annotated[str, StringConstraints(
       to_lower=True, pattern=r"^[a-zA-Z0-9]+_[a-zA-Z0-9]+_[a-zA-Z0-9]+$" 
    )] = Field(examples=["frg_1_test"])
    hostname: Annotated[str, StringConstraints(
       to_lower=True
    )] = Field(examples=["W10TEST"])
 

class RigBase(RigInput):
    rig_type: str
    comp_type: str
    instance: str


class Rig(RigBase):
    id: int


PartialRigInput = partial_model(RigInput)
