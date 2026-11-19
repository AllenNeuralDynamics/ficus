import pytest
from pydantic import ValidationError

from ficus.core.config import Settings


def test_scopes_keep_their_order():
    assert Settings(scopes=["subject_id", "hostname"]).scopes == ["subject_id", "hostname"]


@pytest.mark.parametrize("scopes", [["hostname", "hostname"], ["mode"]])
def test_scopes_reject_duplicates_and_mode(scopes):
    with pytest.raises(ValidationError):
        Settings(scopes=scopes)
