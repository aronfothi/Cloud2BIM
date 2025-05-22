"""
Test point cloud loading and processing functionality of CloudToBimProcessor.
"""
import pytest
import os
import shutil
import numpy as np
from pathlib import Path
import open3d as o3d

from app.core.cloud2entities import CloudToBimProcessor

# Constants
TESTS_DIR = Path(__file__).parent.parent.parent
DATA_DIR = TESTS_DIR / "data"
SAMPLE_PTX = DATA_DIR / "scan6.ptx"
SAMPLE_CONFIG_YAML = DATA_DIR / "sample_config.yaml"

@pytest.fixture
def point_cloud_files(tmp_path):
    """Create test point cloud files in different formats."""
    # Create a simple point cloud for testing
    pcd = o3d.geometry.PointCloud()
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]])  # Simple square
    pcd.points = o3d.utility.Vector3dVector(points)
    
    # Save in different formats
    ply_path = tmp_path / "test.ply"
    xyz_path = tmp_path / "test.xyz"
    o3d.io.write_point_cloud(str(ply_path), pcd)
    np.savetxt(xyz_path, points)  # Simple XYZ format
    
    # Copy the sample PTX file
    ptx_path = tmp_path / SAMPLE_PTX.name
    shutil.copy(SAMPLE_PTX, ptx_path)
    
    return {
        'ply': ply_path,
        'xyz': xyz_path,
        'ptx': ptx_path
    }

@pytest.fixture
def processor_setup(tmp_path, point_cloud_files):
    """Set up a CloudToBimProcessor instance with test files."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    
    # Copy test files to input directory
    for file_path in point_cloud_files.values():
        shutil.copy(file_path, input_dir)
    
    config = {
        'input': {
            'point_cloud': {
                'file_path': str(input_dir / SAMPLE_PTX.name)
            }
        },
        'processing': {
            'voxel_size': 0.05,
            'min_points': 100
        }
    }
    
    processor = CloudToBimProcessor(
        job_id="test-job",
        config_data=config,
        input_dir=str(input_dir),
        output_dir=str(output_dir)
    )
    
    return processor, input_dir, output_dir

def test_load_ptx_file(processor_setup, point_cloud_files):
    """Test loading a PTX file."""
    processor, _, _ = processor_setup
    
    # Test loading PTX file
    pcd = processor._load_point_cloud(point_cloud_files['ptx'])
    assert pcd is not None
    assert isinstance(pcd, o3d.geometry.PointCloud)
    assert len(pcd.points) > 0

def test_load_xyz_file(processor_setup, point_cloud_files):
    """Test loading an XYZ file."""
    processor, _, _ = processor_setup
    
    # Test loading XYZ file
    pcd = processor._load_point_cloud(point_cloud_files['xyz'])
    assert pcd is not None
    assert isinstance(pcd, o3d.geometry.PointCloud)
    assert len(pcd.points) == 4  # Our test square has 4 points

def test_load_ply_file(processor_setup, point_cloud_files):
    """Test loading a PLY file."""
    processor, _, _ = processor_setup
    
    # Test loading PLY file
    pcd = processor._load_point_cloud(point_cloud_files['ply'])
    assert pcd is not None
    assert isinstance(pcd, o3d.geometry.PointCloud)
    assert len(pcd.points) == 4  # Our test square has 4 points

def test_invalid_point_cloud_file(processor_setup):
    """Test loading an invalid point cloud file."""
    processor, input_dir, _ = processor_setup
    
    # Create an invalid file
    invalid_file = input_dir / "invalid.ptx"
    invalid_file.write_text("This is not a valid point cloud file")
    
    with pytest.raises(Exception):  # The specific exception type depends on your implementation
        processor._load_point_cloud(invalid_file)

def test_process_point_cloud(processor_setup, point_cloud_files):
    """Test the point cloud processing pipeline."""
    processor, _, _ = processor_setup
    
    # Load and process the sample PTX file
    pcd = processor._load_point_cloud(point_cloud_files['ptx'])
    processed_pcd = processor._process_point_cloud(pcd)
    
    assert processed_pcd is not None
    assert isinstance(processed_pcd, o3d.geometry.PointCloud)
    assert len(processed_pcd.points) > 0
    # Add more specific assertions based on your processing steps
