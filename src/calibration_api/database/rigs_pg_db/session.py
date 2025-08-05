from sqlalchemy import create_engine, URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from typing import Any, Generator


# TODO: Probably want to move this to a config class somewhere else
# TODO: Pull credentials from keepass
url_object = URL.create(
    "postgresql+psycopg2",
    username="calibration",
    password="squirtleIsATurt13",
    # host="eng-tools",
    host="localhost",
    port=5432,
    database="calibration",
)


class Base(DeclarativeBase):
    pass


engine = create_engine(url_object)


# TODO: what is autoflush and autocommit. Should these be set to true or false?
local_session = sessionmaker(bind=engine)


def get_db() -> Generator[Any, Any, Any]:
    db = local_session()
    # TODO: this creates the tables when calling endpoint...
    #       should create table on load... I think I need to import models here first
    Base.metadata.create_all(engine)  # Create tables if they don't exist
    try:
        yield db
    finally:
        db.close()
