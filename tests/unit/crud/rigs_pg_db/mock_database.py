import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from calibration_api.database.rigs_pg_db.session import Base
from calibration_api.database.rigs_pg_db.models.rigs import Rigs  # noqa: F401


@pytest.fixture(scope="function")
def db_session():
    """Fixture for creating a new database session. This database is in memory and resets after each test."""
    # Create an in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    
    # Create the tables
    Base.metadata.create_all(engine)
    
    # Create a new session
    Session = sessionmaker(bind=engine)
    session = Session()
    try: 
        yield session
    finally:
        Base.metadata.drop_all(engine)
        session.close()
