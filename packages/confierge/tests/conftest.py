import pytest


@pytest.fixture(scope="session")
def store_structure():
    """Minimal data store layout used by both integration and (future) service-level tests."""
    return {
        "scratch": {
            "defaults": {
                "software_a": {
                    "default.yml": {"default-default-value": "the one ring"},
                    "config.yml": {
                        "name": "config",
                        "scope": "default",
                        "default-layer-value": "beep beep",
                    },
                },
            },
            "hostname": {
                "w11dt000001": {
                    "software_a": {
                        "config.yml": {"computer-layer-value": "boop boop"},
                    }
                }
            },
            "subject_id": {
                "614173": {
                    "software_a": {
                        "config.yml": {
                            "subject-layer-value": "bap bap",
                            "scope": "614173",
                        }
                    }
                }
            },
        }
    }
