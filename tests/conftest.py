import json
import pytest

@pytest.fixture
def encode_data():
    def _encode(data: dict) -> bytes:
        return json.dumps(data).encode()
    return _encode
