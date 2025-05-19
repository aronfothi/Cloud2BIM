"""
This module contains pytest fixtures that can be reused across multiple test files.
"""
import os
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app

@pytest.fixture
def test_client():
    """Create a test client for making HTTP requests."""
    return TestClient(app)

@pytest.fixture
def sample_ptx_file():
    """Create a sample PTX file for testing."""
    # TODO: Add sample PTX data
    test_data_dir = Path(__file__).parent / "data"
    ptx_path = test_data_dir / "sample.ptx"
    return ptx_path

@pytest.fixture
def sample_config_file():
    """Create a sample YAML config file for testing."""
    # TODO: Add sample config data
    test_data_dir = Path(__file__).parent / "data"
    config_path = test_data_dir / "sample_config.yaml"
    return config_path
