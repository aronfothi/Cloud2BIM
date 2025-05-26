"""Test the API endpoints."""

import pytest
from pathlib import Path
import uuid
import json


def test_convert_endpoint(test_client, sample_ptx_file, sample_config_file):
    """Test the /convert endpoint with valid input files."""
    # Prepare test files
    with open(sample_ptx_file, "rb") as ptx, open(sample_config_file, "rb") as config:
        files = {
            "point_cloud": ("sample.ptx", ptx, "application/octet-stream"),
            "config": ("config.yaml", config, "application/x-yaml"),
        }
        response = test_client.post("/convert", files=files)

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert uuid.UUID(data["job_id"])  # Validate UUID format


def test_status_endpoint(test_client):
    """Test the /status/{job_id} endpoint."""
    # Test with non-existent job ID
    fake_job_id = str(uuid.uuid4())
    response = test_client.get(f"/status/{fake_job_id}")
    assert response.status_code == 404

    # TODO: Test with real job ID after implementing job creation fixture


def test_results_endpoint_model_ifc(test_client):
    """Test the /results/{job_id}/model.ifc endpoint."""
    # Test with non-existent job ID
    fake_job_id = str(uuid.uuid4())
    response = test_client.get(f"/results/{fake_job_id}/model.ifc")
    assert response.status_code == 404

    # TODO: Test with completed job ID after implementing job creation fixture


def test_results_endpoint_point_mapping(test_client):
    """Test the /results/{job_id}/point_mapping.json endpoint."""
    # Test with non-existent job ID
    fake_job_id = str(uuid.uuid4())
    response = test_client.get(f"/results/{fake_job_id}/point_mapping.json")
    assert response.status_code == 404

    # TODO: Test with completed job ID after implementing job creation fixture
