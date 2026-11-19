import pytest
from fastapi.testclient import TestClient

from dwg.main import app


@pytest.fixture
def client():
    """Provides a clean TestClient instance for every test."""
    with TestClient(app) as c:
        yield c
