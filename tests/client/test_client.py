"""Unit tests for the Cloud2BIM client."""
import pytest
import os
import tempfile
import numpy as np
import open3d as o3d
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
import json
import shutil
from requests.exceptions import RequestException
import requests

from client.client import (
    read_point_cloud,
    read_ptx_file,
    merge_point_clouds,
    upload_files,
    poll_job_status,
    download_result_file,
    SUPPORTED_FORMATS
)

# Test data setup
TESTS_DIR = Path(__file__).parent.parent
DATA_DIR = TESTS_DIR / "data"
TEST_CLEAN_PTX = DATA_DIR / "test_clean.ptx"
SCAN5_PTX = DATA_DIR / "scan5.ptx"
SCAN6_PTX = DATA_DIR / "scan6.ptx"

@pytest.fixture(autouse=True)
def cleanup():
    """Clean up any temporary files after each test."""
    yield
    # Cleanup will happen automatically as tmp_path is a pytest fixture

@pytest.fixture
def sample_point_clouds(tmp_path):
    """Create sample point cloud files in different formats for testing."""
    # Create a simple point cloud
    pcd = o3d.geometry.PointCloud()
    points = np.array([
        [0, 0, 0], [1, 0, 0], [0, 1, 0],  # Triangle
        [1, 1, 0], [0.5, 0.5, 1]  # Additional points
    ])
    colors = np.array([
        [1, 0, 0], [0, 1, 0], [0, 0, 1],  # RGB colors
        [1, 1, 0], [1, 0, 1]
    ])
    pcd.points = o3d.utility.Vector3dVector(points)
    pcd.colors = o3d.utility.Vector3dVector(colors)
    
    # Save in different formats
    ply_path = tmp_path / "test.ply"
    xyz_path = tmp_path / "test.xyz"
    o3d.io.write_point_cloud(str(ply_path), pcd)
    np.savetxt(xyz_path, points)  # XYZ format only saves points
    
    # Copy PTX test files
    ptx_paths = []
    for ptx_file in [SCAN5_PTX, SCAN6_PTX]:
        if ptx_file.exists():
            ptx_copy = tmp_path / ptx_file.name
            shutil.copy(ptx_file, ptx_copy)
            ptx_paths.append(ptx_copy)
    # Fall back to test clean PTX if scan files not available
    if not ptx_paths and TEST_CLEAN_PTX.exists():
        test_ptx_copy = tmp_path / TEST_CLEAN_PTX.name
        shutil.copy(TEST_CLEAN_PTX, test_ptx_copy)
        ptx_paths = [test_ptx_copy]
    
    return {
        'ply': ply_path,
        'xyz': xyz_path,
        'ptx_files': ptx_paths,
        'original_pcd': pcd
    }

@pytest.fixture
def minimal_ptx_path():
    """Return path to the minimal test PTX file."""
    return DATA_DIR / "test_clean.ptx"

@pytest.fixture
def mock_server():
    """Mock server responses for testing."""
    with patch('client.client.requests') as mock_requests:
        # Mock successful job creation
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {'job_id': 'test-job-123'}
        mock_post_response.raise_for_status.return_value = None
        
        # Mock successful status check
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            'status': 'completed',
            'progress': 100,
            'stage': 'Finished',
            'message': 'Success'
        }
        mock_get_response.raise_for_status.return_value = None
        
        # Mock successful file download
        mock_download_response = MagicMock()
        mock_download_response.iter_content.return_value = iter([b'test content'])
        mock_download_response.raise_for_status.return_value = None
        
        # Set up the mock get to return different responses based on URL
        def get_side_effect(*args, **kwargs):
            if 'status' in args[0]:
                return mock_get_response
            elif 'results' in args[0]:
                return mock_download_response
            return mock_get_response
            
        mock_requests.get.side_effect = get_side_effect
        mock_requests.post.return_value = mock_post_response
        mock_requests.RequestException = RequestException
        
        yield mock_requests

def test_read_point_cloud_ply(sample_point_clouds):
    """Test reading a PLY point cloud file."""
    pcd = read_point_cloud(str(sample_point_clouds['ply']))
    assert pcd is not None
    assert len(pcd.points) == 5
    assert len(pcd.colors) == 5  # PLY preserves colors

def test_read_point_cloud_xyz(sample_point_clouds):
    """Test reading an XYZ point cloud file."""
    pcd = read_point_cloud(str(sample_point_clouds['xyz']))
    assert pcd is not None
    assert len(pcd.points) == 5
    assert not pcd.has_colors()  # XYZ doesn't store colors

@pytest.mark.skipif(not TEST_CLEAN_PTX.exists(), reason="Test PTX file not available")
def test_read_point_cloud_ptx(sample_point_clouds):
    """Test reading a PTX point cloud file."""
    pcd = read_point_cloud(str(sample_point_clouds['ptx_files'][1]))
    assert pcd is not None
    assert len(pcd.points) > 0

def test_read_point_cloud_invalid_file(tmp_path):
    """Test reading an invalid point cloud file."""
    invalid_file = tmp_path / "invalid.ply"
    invalid_file.write_text("This is not a valid point cloud file")
    
    pcd = read_point_cloud(str(invalid_file))
    assert pcd is None

def test_merge_point_clouds(sample_point_clouds):
    """Test merging multiple point cloud files."""
    files_to_merge = [
        str(sample_point_clouds['ply']),
        str(sample_point_clouds['xyz'])
    ]
    
    merged_pcd = merge_point_clouds(files_to_merge)
    assert merged_pcd is not None
    # Should have points from both files
    assert len(merged_pcd.points) == 10  # 5 points from each file
    # Colors might not be preserved from XYZ file

def test_merge_point_clouds_empty_list():
    """Test merging an empty list of point clouds."""
    merged_pcd = merge_point_clouds([])
    assert merged_pcd is None

def test_merge_point_clouds_invalid_file(sample_point_clouds, tmp_path):
    """Test merging with an invalid file in the list."""
    invalid_file = tmp_path / "invalid.ply"
    invalid_file.write_text("This is not a valid point cloud file")
    
    files_to_merge = [
        str(sample_point_clouds['ply']),
        str(invalid_file)
    ]
    
    merged_pcd = merge_point_clouds(files_to_merge)
    assert merged_pcd is not None
    assert len(merged_pcd.points) == 5  # Only points from valid file

def test_upload_files_success(mock_server, sample_point_clouds, tmp_path):
    """Test successful file upload."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("test: config")
    
    job_id = upload_files(
        "http://localhost:8000",
        str(sample_point_clouds['ply']),
        str(config_file)
    )
    
    assert job_id == 'test-job-123'
    mock_server.post.assert_called_once()

def test_upload_files_missing_file(mock_server):
    """Test upload with missing files."""
    job_id = upload_files(
        "http://localhost:8000",
        "nonexistent.ply",
        "nonexistent.yaml"
    )
    assert job_id is None
    mock_server.post.assert_not_called()

def test_poll_job_status_success(mock_server):
    """Test successful job status polling."""
    status = poll_job_status("http://localhost:8000", "test-job-123")
    assert status['status'] == 'completed'
    assert status['progress'] == 100
    mock_server.get.assert_called()

def test_poll_job_status_server_error(mock_server):
    """Test job status polling with server error."""
    mock_server.get.side_effect = RequestException("Server error")
    status = poll_job_status("http://localhost:8000", "test-job-123")
    assert status is None

def test_download_result_file_success(mock_server, tmp_path):
    """Test successful result file download."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    success = download_result_file(
        "http://localhost:8000",
        "test-job-123",
        "model.ifc",
        str(output_dir)
    )
    
    assert success
    assert (output_dir / "test-job-123_model.ifc").exists()
    mock_server.get.assert_called()

def test_download_result_file_server_error(mock_server, tmp_path):
    """Test result file download with server error."""
    mock_server.get.side_effect = Exception("Server error")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    success = download_result_file(
        "http://localhost:8000",
        "test-job-123",
        "model.ifc",
        str(output_dir)
    )
    
    assert not success
    assert not (output_dir / "test-job-123_model.ifc").exists()

def test_read_ptx_file():
    """Test reading individual PTX files."""
    if not TEST_CLEAN_PTX.exists():
        pytest.skip("Test PTX file not available")

    points, colors = read_ptx_file(str(TEST_CLEAN_PTX))
        
    assert points is not None
    assert len(points) > 0
    assert points.shape[1] == 3  # Each point should have x, y, z
    if colors is not None:
        assert len(colors) == len(points)
        assert colors.shape[1] == 3  # Each color should have r, g, b
        assert np.all((colors >= 0) & (colors <= 1))  # Colors should be normalized

def test_read_point_cloud_ptx():
    """Test reading PTX files through the general point cloud reader."""
    if not TEST_CLEAN_PTX.exists():
        pytest.skip("Test PTX file not available")

    pcd = read_point_cloud(str(TEST_CLEAN_PTX))
        
    assert pcd is not None
    assert len(pcd.points) > 0
    assert isinstance(pcd, o3d.geometry.PointCloud)

def test_merge_ptx_files():
    """Test merging multiple PTX files."""
    if not (SCAN5_PTX.exists() and SCAN6_PTX.exists()):
        pytest.skip("Sample scan PTX files not available")

    # Use both scan files for merging
    ptx_files = [str(SCAN5_PTX), str(SCAN6_PTX)]
    merged_pcd = merge_point_clouds(ptx_files)

    assert merged_pcd is not None
    assert len(merged_pcd.points) > 0

    # Load individual files and verify merge
    scan5_pcd = read_point_cloud(str(SCAN5_PTX))
    scan6_pcd = read_point_cloud(str(SCAN6_PTX))
    
    assert scan5_pcd is not None and scan6_pcd is not None, "Both scan files should be readable"
    expected_points = len(scan5_pcd.points) + len(scan6_pcd.points)
    assert len(merged_pcd.points) == expected_points, "Merged point cloud should contain points from both files"
    assert merged_pcd.has_colors(), "Should preserve colors after merging"

def test_merge_ptx_with_other_formats(sample_point_clouds):
    """Test merging PTX files with other point cloud formats."""
    if not sample_point_clouds['ptx_files']:
        pytest.skip("Sample PTX files not available")

    files_to_merge = [
        str(sample_point_clouds['ply']),
        str(sample_point_clouds['ptx_files'][0])
    ]

    merged_pcd = merge_point_clouds(files_to_merge)
    assert merged_pcd is not None
    assert len(merged_pcd.points) > 0

    # Should have points from both files
    ply_pcd = read_point_cloud(str(sample_point_clouds['ply']))
    ptx_pcd = read_point_cloud(str(sample_point_clouds['ptx_files'][0]))
    assert ply_pcd is not None and ptx_pcd is not None
    assert len(merged_pcd.points) == len(ply_pcd.points) + len(ptx_pcd.points)
    # Merged cloud should contain all original points and colors
    assert merged_pcd.has_colors()

def test_read_ptx_minimal(minimal_ptx_path):
    """Test reading a minimal PTX file."""
    pcd = read_point_cloud(str(minimal_ptx_path))
    assert pcd is not None
    assert len(pcd.points) == 6  # Our minimal file has 6 points
    assert pcd.has_colors()  # Should have colors
    assert len(pcd.colors) == len(pcd.points)  # Should have colors for all points
    
    # Verify points and colors are valid
    points = np.asarray(pcd.points)
    colors = np.asarray(pcd.colors)
    assert points.shape[1] == 3  # Each point should have x, y, z
    assert colors.shape[1] == 3  # Each color should have r, g, b
    assert np.all((colors >= 0) & (colors <= 1))  # Colors should be normalized

def test_read_ptx_with_subsampling(minimal_ptx_path):
    """Test reading a PTX file with subsampling."""
    # First read without subsampling to get baseline
    pcd_full = read_point_cloud(str(minimal_ptx_path), subsample=1)
    assert pcd_full is not None
    full_points = len(pcd_full.points)
    
    # Read with subsampling factor of 2
    pcd_subsampled = read_point_cloud(str(minimal_ptx_path), subsample=2)
    assert pcd_subsampled is not None
    subsampled_points = len(pcd_subsampled.points)
    
    # The subsampled point cloud should have roughly half the points
    # Allow for some variance due to rounding
    assert 0.4 * full_points <= subsampled_points <= 0.6 * full_points
