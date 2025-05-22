"""
Test detection functionality (slabs, walls, openings, zones) of CloudToBimProcessor.
"""
import pytest
import numpy as np
import open3d as o3d
from pathlib import Path

from app.core.cloud2entities import CloudToBimProcessor

# Constants
TESTS_DIR = Path(__file__).parent.parent.parent
DATA_DIR = TESTS_DIR / "data"
SAMPLE_PTX = DATA_DIR / "scan6.ptx"

@pytest.fixture
def simple_room_point_cloud():
    """Create a simple synthetic room point cloud for testing."""
    # Create a simple box-shaped room with points on the walls, floor, and ceiling
    pcd = o3d.geometry.PointCloud()
    
    # Room dimensions
    width, length, height = 4.0, 6.0, 3.0
    points_per_surface = 1000
    
    # Generate points for floor (XY plane at Z=0)
    floor_points = np.random.rand(points_per_surface, 2)
    floor_points = floor_points * [width, length]
    floor_points = np.column_stack([floor_points, np.zeros(points_per_surface)])
    
    # Generate points for ceiling (XY plane at Z=height)
    ceiling_points = np.random.rand(points_per_surface, 2)
    ceiling_points = ceiling_points * [width, length]
    ceiling_points = np.column_stack([ceiling_points, np.full(points_per_surface, height)])
    
    # Generate points for walls
    # Front wall (YZ plane at X=0)
    front_wall_points = np.random.rand(points_per_surface, 2)
    front_wall_points = front_wall_points * [length, height]
    front_wall_points = np.column_stack([np.zeros(points_per_surface), front_wall_points])
    
    # Back wall (YZ plane at X=width)
    back_wall_points = np.random.rand(points_per_surface, 2)
    back_wall_points = back_wall_points * [length, height]
    back_wall_points = np.column_stack([np.full(points_per_surface, width), back_wall_points])
    
    # Left wall (XZ plane at Y=0)
    left_wall_points = np.random.rand(points_per_surface, 2)
    left_wall_points = left_wall_points * [width, height]
    left_wall_points = np.column_stack([left_wall_points[:, 0], np.zeros(points_per_surface), left_wall_points[:, 1]])
    
    # Right wall (XZ plane at Y=length)
    right_wall_points = np.random.rand(points_per_surface, 2)
    right_wall_points = right_wall_points * [width, height]
    right_wall_points = np.column_stack([right_wall_points[:, 0], np.full(points_per_surface, length), right_wall_points[:, 1]])
    
    # Combine all points
    all_points = np.vstack([
        floor_points,
        ceiling_points,
        front_wall_points,
        back_wall_points,
        left_wall_points,
        right_wall_points
    ])
    
    pcd.points = o3d.utility.Vector3dVector(all_points)
    
    # Add a small amount of noise
    pcd.points = o3d.utility.Vector3dVector(
        np.asarray(pcd.points) + np.random.normal(0, 0.02, size=np.asarray(pcd.points).shape)
    )
    
    return pcd

@pytest.fixture
def processor_with_simple_room(tmp_path, simple_room_point_cloud):
    """Set up a CloudToBimProcessor with a simple room point cloud."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    
    # Save the synthetic point cloud
    pcd_path = input_dir / "simple_room.ply"
    o3d.io.write_point_cloud(str(pcd_path), simple_room_point_cloud)
    
    config = {
        'input': {
            'point_cloud': {
                'file_path': str(pcd_path)
            }
        },
        'processing': {
            'voxel_size': 0.05,
            'min_points': 100,
            'wall_thickness': 0.2,
            'floor_ceiling_thickness': 0.3
        }
    }
    
    processor = CloudToBimProcessor(
        job_id="test-detection",
        config_data=config,
        input_dir=str(input_dir),
        output_dir=str(output_dir)
    )
    
    return processor, simple_room_point_cloud

def test_slab_detection(processor_with_simple_room):
    """Test detection of floor and ceiling slabs."""
    processor, _ = processor_with_simple_room
    
    # Process point cloud and detect slabs
    slabs = processor._detect_slabs()
    
    assert len(slabs) == 2  # Should detect floor and ceiling
    # Verify slab properties (height, orientation, etc.)
    heights = [slab.height for slab in slabs]
    assert min(heights) < 0.5  # Floor should be near z=0
    assert max(heights) > 2.5  # Ceiling should be near z=3.0

def test_wall_detection(processor_with_simple_room):
    """Test detection of walls."""
    processor, _ = processor_with_simple_room
    
    # Process point cloud and detect walls
    walls = processor._detect_walls()
    
    assert len(walls) == 4  # Should detect 4 walls
    # Verify wall properties (orientation, position, etc.)
    for wall in walls:
        assert wall.height > 2.0  # Walls should be tall
        assert wall.width > 1.0   # Walls should be wide

def test_opening_detection(processor_with_simple_room):
    """Test detection of openings (windows/doors) in walls."""
    processor, pcd = processor_with_simple_room
    
    # Add a door-shaped hole in one wall
    wall_points = np.asarray(pcd.points)
    # Remove points in a door-shaped region
    door_mask = (
        (wall_points[:, 0] < 0.1) &  # Front wall
        (wall_points[:, 1] > 2) &    # Door position
        (wall_points[:, 1] < 3) &    # Door width
        (wall_points[:, 2] < 2.2)    # Door height
    )
    pcd.points = o3d.utility.Vector3dVector(wall_points[~door_mask])
    
    # Detect openings
    openings = processor._detect_openings()
    
    assert len(openings) > 0  # Should detect at least one opening
    # Verify opening properties
    opening = openings[0]
    assert 1.8 < opening.height < 2.4  # Typical door height
    assert 0.8 < opening.width < 1.2   # Typical door width

def test_zone_detection(processor_with_simple_room):
    """Test detection of zones/rooms."""
    processor, _ = processor_with_simple_room
    
    # Detect zones
    zones = processor._detect_zones()
    
    assert len(zones) == 1  # Should detect one room
    zone = zones[0]
    assert 20 < zone.area < 30  # Room area should be approximately width * length
    assert 2.8 < zone.height < 3.2  # Room height should be approximately 3.0
