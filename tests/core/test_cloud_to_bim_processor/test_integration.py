"""
Tests the integration between CloudToBimProcessor and client components.
"""
import os
import uuid
import pytest
import tempfile
import numpy as np
import ifcopenshell
import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.core.cloud2entities import CloudToBimProcessor
from app.core.aux_functions import load_config_and_variables
from client.client import read_point_cloud, merge_point_clouds

class TestCloudToBimIntegration:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment for each test."""
        self.test_data_dir = Path(__file__).parent.parent.parent / "tests" / "data"
        self.ptx_file_path = self.test_data_dir / "scan6.ptx"
        self.config_file_path = self.test_data_dir / "sample_config.yaml"

        # Skip if test files don't exist
        if not self.ptx_file_path.exists():
            pytest.skip(f"Test PTX file not found: {self.ptx_file_path}")
        if not self.config_file_path.exists():
            pytest.skip(f"Test config file not found: {self.config_file_path}")

        # Create temp directories for input/output
        self.test_dir = tempfile.TemporaryDirectory()
        self.job_id = str(uuid.uuid4())
        self.input_dir = Path(self.test_dir.name) / "input"
        self.output_dir = Path(self.test_dir.name) / "output"
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Create test client
        self.client = TestClient(app)

        yield

        # Cleanup
        self.test_dir.cleanup()

    def test_cloud_to_bim_end_to_end(self):
        """Test complete process from point cloud to IFC using client and server components."""
        # 1. Client-side: Read and prepare point cloud
        pcd = read_point_cloud(str(self.ptx_file_path))
        assert pcd is not None, "Failed to read point cloud file"

        # Convert point cloud to standard format for transmission
        points = np.asarray(pcd.points).tolist()
        colors = np.asarray(pcd.colors).tolist() if pcd.has_colors() else None
        
        # Prepare point cloud data in standard format
        point_cloud_data = {
            "points": points,
            "colors": colors,
            "format": "ptx",
            "filename": self.ptx_file_path.name
        }

        # 2. Read configuration
        with open(self.config_file_path, 'r') as f:
            config_data = f.read()

        # 3. Client-side: Prepare multipart form data
        files = {
            'point_cloud': ('point_cloud.json', json.dumps(point_cloud_data), 'application/json'),
            'config': ('config.yaml', config_data, 'application/x-yaml')
        }

        # 4. Client-side: Send request to server
        response = self.client.post("/api/v1/jobs/", files=files)
        assert response.status_code == 200, f"Failed to create job: {response.text}"
        
        job_data = response.json()
        job_id = job_data['job_id']

        # 5. Client-side: Poll for job completion
        max_polls = 30
        poll_interval = 1
        import time

        for _ in range(max_polls):
            response = self.client.get(f"/api/v1/jobs/{job_id}/status")
            assert response.status_code == 200
            
            status = response.json()
            if status['status'] == 'completed':
                break
            elif status['status'] == 'failed':
                pytest.fail(f"Job failed: {status.get('message', 'Unknown error')}")
            
            time.sleep(poll_interval)
        else:
            pytest.fail("Job timed out")

        # 6. Client-side: Download results
        response = self.client.get(f"/api/v1/jobs/{job_id}/results/model.ifc")
        assert response.status_code == 200

        # Save IFC file
        ifc_file_path = self.output_dir / f"{job_id}_model.ifc"
        ifc_file_path.write_bytes(response.content)

        # 7. Validate IFC model structure
        ifc_model = ifcopenshell.open(str(ifc_file_path))

        # Check basic IFC structure
        projects = ifc_model.by_type("IfcProject")
        assert len(projects) == 1, "Expected exactly one IfcProject"

        sites = ifc_model.by_type("IfcSite")
        assert len(sites) == 1, "Expected exactly one IfcSite"

        buildings = ifc_model.by_type("IfcBuilding")
        assert len(buildings) == 1, "Expected exactly one IfcBuilding"

        # Verify expected entities from scan6.ptx
        slabs = ifc_model.by_type("IfcSlab")
        assert len(slabs) == 2, f"Expected 2 slabs, found {len(slabs)}"

        walls = ifc_model.by_type("IfcWall") + ifc_model.by_type("IfcWallStandardCase")
        assert len(walls) > 0, "Expected at least one wall"

        # 8. Check point mapping file
        response = self.client.get(f"/api/v1/jobs/{job_id}/results/point_mapping.json")
        assert response.status_code == 200
        
        mapping_data = response.json()
        assert 'slabs' in mapping_data, "Point mapping should include slabs"
        assert 'walls' in mapping_data, "Point mapping should include walls"

    def test_error_handling_invalid_point_cloud(self):
        """Test server's handling of invalid point cloud data."""
        # Prepare invalid point cloud data
        invalid_point_cloud = {
            "points": [[0, 0, 0]],  # Too few points
            "colors": None,
            "format": "ptx"
        }

        with open(self.config_file_path, 'r') as f:
            config_data = f.read()

        files = {
            'point_cloud': ('point_cloud.json', json.dumps(invalid_point_cloud), 'application/json'),
            'config': ('config.yaml', config_data, 'application/x-yaml')
        }

        response = self.client.post("/api/v1/jobs/", files=files)
        assert response.status_code == 400, "Should reject invalid point cloud data"

    def test_error_handling_invalid_config(self):
        """Test server's handling of invalid configuration."""
        # Prepare valid point cloud data
        pcd = read_point_cloud(str(self.ptx_file_path))
        point_cloud_data = {
            "points": np.asarray(pcd.points).tolist(),
            "colors": np.asarray(pcd.colors).tolist() if pcd.has_colors() else None,
            "format": "ptx"
        }

        # Invalid config
        invalid_config = "invalid: : yaml:"

        files = {
            'point_cloud': ('point_cloud.json', json.dumps(point_cloud_data), 'application/json'),
            'config': ('config.yaml', invalid_config, 'application/x-yaml')
        }

        response = self.client.post("/api/v1/jobs/", files=files)
        assert response.status_code == 400, "Should reject invalid config"
