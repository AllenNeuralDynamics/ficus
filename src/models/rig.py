from pydantic import BaseModel
from src.models.partial import partial_model


class Rig(BaseModel):
    rig_type: str
    comp_type: str
    instance: str
    host_name: str


class RigDB(Rig):
    id: int
    rig_name: str


PartialRig = partial_model(Rig, ["rig_type"])
PartialRigDB = partial_model(RigDB)
