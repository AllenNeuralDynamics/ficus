from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from calibration_api.database.session import Base


class Calibrations(Base):
    __tablename__ = "calibrations"
    id: Mapped[int] = mapped_column(primary_key=True)
    rig_id: Mapped[int] = mapped_column(ForeignKey("rigs.id"))
    device_name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    date: Mapped[datetime] = mapped_column(DateTime)
    input_data: Mapped[JSON] = mapped_column(JSON)
    output_data: Mapped[JSON] = mapped_column(JSON)
    notes: Mapped[str] = mapped_column(String)

    def __repr__(self) -> str:
        return f"Tables(id={self.id}, rig_id={self.rig_id}, device_name={self.device_name}, " \
               f"description={self.description}, date={self.date}, input_data={self.input_data}, " \
               f"output_data={self.output_data}, notes={self.notes})"
