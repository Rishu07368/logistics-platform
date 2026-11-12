import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.app import create_app  # noqa: E402


@pytest.fixture()
def client(tmp_path):
    return create_app(str(tmp_path / "test.db")).test_client()
