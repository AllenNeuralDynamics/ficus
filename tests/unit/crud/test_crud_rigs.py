import pytest

from fastapi import HTTPException
from tests.unit.mock_database import Rigs, db_session  # noqa: F401

from calibration_api.crud.rigs_pg_db.rigs import get_rigs, get_rig_by_name, create_rigs, update_rig, delete_rig_by_name
from calibration_api.database.rigs_pg_db.schemas.rig import RigAddUpdate, PartialRigAddUpdate


@pytest.fixture(scope="function")
def db_test(db_session):  # noqa: F811
    """Fixture for creating test rigs for the tests."""
    rigs_to_create = [
        RigAddUpdate(**{"rig_name": "frg_1_prod", "hostname": "W10TESTf1"}),
        RigAddUpdate(**{"rig_name": "BEH_1_test", "hostname": "W10TESTb1"}),
        RigAddUpdate(**{"rig_name": "BEH_2_test", "hostname": "W10TESTb2"}),
    ]
    create_rigs(db_session, rigs_to_create)

    yield db_session


################################################################################
#
#   get_rig tests
#
################################################################################


def test_get_rigs(db_test):
    """Test fetching rigs from the database."""
    # No filters - should return everything
    results = get_rigs(db_test)
    assert len(results) == 3
    assert results[0].rig_name == "frg_1_prod"
    assert results[1].rig_name == "beh_1_test"

    # Rig type filter
    results = get_rigs(db_test, rig_type="FRG")
    assert len(results) == 1
    assert results[0].rig_name == "frg_1_prod"

    # Instance filter
    results = get_rigs(db_test, instance="1")
    assert len(results) == 2

    # Comp type filter
    results = get_rigs(db_test, comp_type="test")
    assert len(results) == 2

    # Hostname filter
    results = get_rigs(db_test, hostname="w10testb2")
    assert len(results) == 1
    assert results[0].rig_name == "beh_2_test"

    # Multiple filters
    results = get_rigs(db_test, comp_type="test", hostname="w10testb2")
    assert len(results) == 1
    assert results[0].rig_name == "beh_2_test"


################################################################################
#
#   get_rig_by_name tests
#
################################################################################


def test_get_rig_by_name(db_test):
    """Test fetching a rig by its name."""

    # Test fetching an existing rig
    result = get_rig_by_name(db_test, "frg_1_prod")
    assert result is not None
    assert result.rig_name == "frg_1_prod"

    # Test fetching a non-existing rig
    with pytest.raises(HTTPException):
        get_rig_by_name(db_test, "frg_1_butt")


################################################################################
#
#   create_rigs tests
#
################################################################################


def test_create_single_rig(db_session):  # noqa: F811
    """Test creating a single rig.
    Note: using the db_session fixture since it needs to test on an empty db.
    """
    rigs_to_create = [RigAddUpdate(**{"rig_name": "FRG_1_test", "hostname": "W10TEST"})]
    create_rigs(db_session, rigs_to_create)
    results = db_session.query(Rigs).first()

    # Should convert to lowercase
    assert results.rig_name == "frg_1_test"
    assert results.hostname == "w10test"


def test_create_multiple_rigs(db_session):  # noqa: F811
    """Test creating a list of rigs.
    Note: using the db_session fixture since it needs to test on an empty db.
    """
    rigs_to_create = [
        RigAddUpdate(**{"rig_name": "frg_2_test", "hostname": "W10TEST1"}),
        RigAddUpdate(**{"rig_name": "FRG_3_test", "hostname": "W10TEST2"}),
    ]
    create_rigs(db_session, rigs_to_create)
    results = db_session.query(Rigs).all()

    assert len(results) == 2
    assert results[0].rig_name == "frg_2_test"
    assert results[1].rig_name == "frg_3_test"


def test_create_existing_rig(db_session):  # noqa: F811
    """Test creating a rig that already exists.
    Note: using the db_session fixture since it needs to test on an empty db.
    """
    rigs_to_create = [RigAddUpdate(**{"rig_name": "frg_1_test", "hostname": "W10TEST"})]
    create_rigs(db_session, rigs_to_create)
    with pytest.raises(HTTPException):
        create_rigs(db_session, rigs_to_create)
    db_session.rollback()

    results = db_session.query(Rigs).all()
    assert len(results) == 1


################################################################################
#
#   update_rig tests
#
################################################################################


def test_update_rig(db_test):
    """Test updating rigs"""
    # Update both rig_name and hostname
    update_rig(db_test, "frg_1_prod", PartialRigAddUpdate(**{"rig_name": "frg_1_new", "hostname": "w10testf1_new"}))
    updated_rig = get_rig_by_name(db_test, "frg_1_new")

    assert updated_rig.rig_name == "frg_1_new"
    assert updated_rig.rig_type == "frg"
    assert updated_rig.instance == "1"
    assert updated_rig.comp_type == "new"
    assert updated_rig.hostname == "w10testf1_new"


def test_update_rig_single_parameter(db_test):
    """Test updating rigs with a single parameter at a time"""
    # Update rig_name only
    update_rig(db_test, "frg_1_prod", PartialRigAddUpdate(**{"rig_name": "frg_1_new"}))
    updated_rig = get_rig_by_name(db_test, "frg_1_new")

    assert updated_rig.rig_name == "frg_1_new"
    assert updated_rig.rig_type == "frg"
    assert updated_rig.instance == "1"
    assert updated_rig.comp_type == "new"
    assert updated_rig.hostname == "w10testf1"

    # Update hostname only
    update_rig(db_test, "frg_1_new", PartialRigAddUpdate(**{"hostname": "w10testf1_new"}))
    updated_rig = get_rig_by_name(db_test, "frg_1_new")

    assert updated_rig.rig_name == "frg_1_new"
    assert updated_rig.rig_type == "frg"
    assert updated_rig.instance == "1"
    assert updated_rig.comp_type == "new"
    assert updated_rig.hostname == "w10testf1_new"


################################################################################
#
#   delete_rig_by_name tests
#
################################################################################


def test_delete_rig_by_name(db_test):
    """Test deleting a rig by its name."""
    initial_rig_count = len(get_rigs(db_test))

    # Delete an existing rig
    delete_rig_by_name(db_test, "frg_1_prod")
    assert len(get_rigs(db_test)) == initial_rig_count - 1
    with pytest.raises(HTTPException):
        get_rig_by_name(db_test, "frg_1_prod")

    # Try to delete a non-existing rig
    with pytest.raises(HTTPException):
        delete_rig_by_name(db_test, "non_existing_rig")
