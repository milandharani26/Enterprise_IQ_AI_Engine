import sys
import os
import pytest

# Add project root to path so 'main' and 'engine' are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)