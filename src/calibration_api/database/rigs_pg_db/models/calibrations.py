import json 

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from calibration_api.database.rigs_pg_db.session import Base


class Calibrations(Base):
    __tablename__ = "calibrations"
    id: Mapped[int] = mapped_column(primary_key=True)
    rig_name: Mapped[int] = mapped_column(ForeignKey("rigs.rig_name"))
    device_name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    date: Mapped[datetime] = mapped_column(DateTime)
    input_data: Mapped[JSON] = mapped_column(JSON)
    output_data: Mapped[JSON] = mapped_column(JSON)
    notes: Mapped[str] = mapped_column(String)

    __table_args__ = (UniqueConstraint("rig_name", "device_name", name="unique_rig_device"),)

    def to_dict(self):
        return {
            "rig_name": self.rig_name,
            "device_name": self.device_name,
            "description": self.description,
            "date": self.date,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "notes": self.notes
        }

    def __repr__(self) -> str:
        return json.dumps({
            "rig_name": self.rig_name,
            "device_name": self.device_name,
            "description": self.description,
            "date": self.date,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "notes": self.notes
        })