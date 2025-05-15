from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from calibration_api.database.session import Base


class Rigs(Base):
    __tablename__ = "rigs"
    id: Mapped[int] = mapped_column(primary_key=True)
    rig_name: Mapped[str] = mapped_column(String, unique=True)
    rig_type: Mapped[str] = mapped_column(String) 
    comp_type: Mapped[str] = mapped_column(String)  
    instance: Mapped[str] = mapped_column(String) 
    hostname: Mapped[str] = mapped_column(String(255)) 

    def __repr__(self) -> str:
        return f"Rigs(id={self.id}, rig_name={self.rig_name}, rig_type={self.rig_type}, " \
               f"comp_type={self.comp_type}, instance={self.instance}, hostname={self.hostname})"
