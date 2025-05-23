"""
Test CloudToBimProcessor with scan6.ptx point cloud data
to verify that exactly 2 slabs are detected and properly 
represented in the IFC model.
"""
import pytest
import os
import numpy as np
import open3d as o3d
import ifcopenshell
from pathlib import Path
import tempfile
import shutil
from uuid import uuid4

from app.core.cloud2entities import CloudToBimProcessor
# Import the custom PTX reader directly by path
import os
import sys
sys.path.append(os.path.dirname(__file__))
from ptx_reader import read_custom_ptx

# Constants
TESTS_DIR = Path(__file__).parent.parent.parent
DATA_DIR = TESTS_DIR / "data"
SCAN6_PTX = DATA_DIR / "scan6.ptx"
SAMPLE_CONFIG = DATA_DIR / "sample_config.yaml"

@pytest.fixture
def temp_dirs():
    """Create temporary input and output directories for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_dir = temp_path / "input"
        output_dir = temp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        yield str(input_dir), str(output_dir)

@pytest.fixture
def basic_config():
    """Create a basic configuration for the CloudToBimProcessor."""
    return {
        "detection": {
            "slab": {
                "thickness": 0.3
            },
            "wall": {
                "thickness": 0.2,
                "min_width": 0.5,
                "min_thickness": 0.08,
                "max_thickness": 0.5
            }
        },
        "preprocessing": {
            "voxel_size": 0.05
        },
        "ifc": {
            "project_name": "Test Project",
            "author_name": "Test",
            "author_surname": "User"
        }
    }

@pytest.mark.skipif(not SCAN6_PTX.exists(), reason="scan6.ptx test file not available")
def test_scan6_slabs_detection():
    """Test that CloudToBimProcessor correctly detects and generates 2 slabs from scan6.ptx."""
    # 1. Read the point cloud using our custom PTX reader
    try:
        pcd = read_custom_ptx(str(SCAN6_PTX), downsample_steps=5)
        assert len(pcd.points) > 0, "scan6.ptx has no points"
    except Exception as e:
        pytest.fail(f"Failed to read scan6.ptx: {str(e)}")
    
    # 2. Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_dir = temp_path / "input"
        output_dir = temp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        
        # 3. Set up configuration
        config = {
            "detection": {
                "slab": {"thickness": 0.3},
                "wall": {
                    "thickness": 0.2,
                    "min_width": 0.5,
                    "min_thickness": 0.08,
                    "max_thickness": 0.5
                }
            },
            "preprocessing": {"voxel_size": 0.05},
            "ifc": {
                "project_name": "Test Project",
                "author_name": "Test",
                "author_surname": "User"
            }
        }
        
        # 4. Create processor with pre-loaded point cloud
        job_id = str(uuid4())
        processor = CloudToBimProcessor(
            job_id=job_id,
            config_data=config,
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            point_cloud_data=pcd  # Pass the pre-loaded point cloud
        )
        
        # 5. Process the point cloud
        processor.process()
        
        # 6. Verify IFC output
        ifc_path = os.path.join(str(output_dir), f"{job_id}_model.ifc")
        assert os.path.exists(ifc_path), f"IFC file not created at {ifc_path}"
        
        # 7. Open IFC and verify slabs
        ifc_model = ifcopenshell.open(ifc_path)
        slabs = ifc_model.by_type("IfcSlab")
        
        # 8. Verify exactly 2 slabs are present
        assert len(slabs) == 2, f"Expected exactly 2 slabs, but found {len(slabs)}"
        
        # 9. Verify slab properties
        for i, slab in enumerate(slabs):
            # Check that each slab has a valid geometry
            assert slab.Representation is not None, f"Slab {i+1} has no geometry representation"
            
            # Check that each slab is assigned to a storey
            decomposed_by = [rel.RelatingObject for rel in ifc_model.by_type("IfcRelContainedInSpatialStructure") 
                            if slab in rel.RelatedElements]
            assert len(decomposed_by) > 0, f"Slab {i+1} is not assigned to any spatial structure"
            
            # Verify the slab has a material assigned
            assert slab.HasAssociations, f"Slab {i+1} has no associations (like materials)"

@pytest.mark.skipif(not SCAN6_PTX.exists(), reason="scan6.ptx test file not available")
def test_scan6_ptx_file_loading():
    """Test that scan6.ptx file can be loaded successfully and contains points."""
    # 1. Check file exists
    assert os.path.isfile(SCAN6_PTX), f"Test file {SCAN6_PTX} does not exist"
    
    # 2. Read the point cloud using our custom PTX reader
    try:
        pcd = read_custom_ptx(str(SCAN6_PTX))
        
        # 3. Verify point cloud has points
        assert pcd is not None, "Failed to create point cloud from scan6.ptx"
        assert len(pcd.points) > 0, f"Point cloud from scan6.ptx has no points"
        
        # 4. Print point cloud size for debugging
        print(f"Successfully loaded scan6.ptx with {len(pcd.points)} points")
        
        # 5. Check for color information
        has_colors = pcd.has_colors()
        if has_colors:
            print(f"Point cloud has color information with {len(pcd.colors)} color entries")
        else:
            print(f"Point cloud does not have color information")
        
        # 6. Check point cloud bounds to verify data looks reasonable
        min_bound = pcd.get_min_bound()
        max_bound = pcd.get_max_bound()
        print(f"Point cloud bounds: Min={min_bound}, Max={max_bound}")
        
    except Exception as e:
        pytest.fail(f"Failed to read scan6.ptx: {str(e)}")
