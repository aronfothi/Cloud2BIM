"""
Test IFC model generation functionality of CloudToBimProcessor.
"""
import pytest
import os
import ifcopenshell
from pathlib import Path

from app.core.cloud2entities import CloudToBimProcessor

# Constants
TESTS_DIR = Path(__file__).parent.parent.parent
DATA_DIR = TESTS_DIR / "data"
SAMPLE_PTX = DATA_DIR / "scan6.ptx"
SAMPLE_CONFIG_YAML = DATA_DIR / "sample_config.yaml"

@pytest.fixture
def mock_detected_elements():
    """Create mock detected elements for testing IFC generation."""
    return {
        'walls': [
            {
                'start_point': (0, 0, 0),
                'end_point': (4, 0, 0),
                'height': 3.0,
                'thickness': 0.2,
                'normal': (0, 1, 0)
            },
            {
                'start_point': (4, 0, 0),
                'end_point': (4, 6, 0),
                'height': 3.0,
                'thickness': 0.2,
                'normal': (-1, 0, 0)
            }
        ],
        'slabs': [
            {
                'points': [(0, 0, 0), (4, 0, 0), (4, 6, 0), (0, 6, 0)],
                'height': 0.0,
                'thickness': 0.3,
                'normal': (0, 0, 1)
            },
            {
                'points': [(0, 0, 3), (4, 0, 3), (4, 6, 3), (0, 6, 3)],
                'height': 3.0,
                'thickness': 0.3,
                'normal': (0, 0, -1)
            }
        ],
        'openings': [
            {
                'parent_wall_index': 0,
                'position': (2, 0, 0.9),
                'width': 1.0,
                'height': 2.1,
                'type': 'door'
            }
        ],
        'zones': [
            {
                'points': [(0, 0, 0), (4, 0, 0), (4, 6, 0), (0, 6, 0)],
                'height': 3.0,
                'name': 'Room 1'
            }
        ]
    }

@pytest.fixture
def processor_setup(tmp_path, mock_detected_elements):
    """Set up a CloudToBimProcessor instance with mock data."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    
    config = {
        'ifc': {
            'project_name': 'Test Project',
            'organization': 'Test Organization',
            'author': 'Test Author',
            'schema_version': 'IFC4',
        },
        'processing': {
            'voxel_size': 0.05,
            'min_points': 100
        }
    }
    
    processor = CloudToBimProcessor(
        job_id="test-ifc",
        config_data=config,
        input_dir=str(input_dir),
        output_dir=str(output_dir)
    )
    
    # Mock the detection results
    processor._detection_results = mock_detected_elements
    
    return processor, input_dir, output_dir

def test_ifc_file_creation(processor_setup):
    """Test that an IFC file is created with the correct schema version."""
    processor, _, output_dir = processor_setup
    
    # Generate IFC file
    ifc_path = processor._generate_ifc_model()
    
    assert os.path.exists(ifc_path)
    ifc_file = ifcopenshell.open(ifc_path)
    assert ifc_file.schema == "IFC4"

def test_ifc_project_setup(processor_setup):
    """Test that the IFC project is set up with correct metadata."""
    processor, _, _ = processor_setup
    
    ifc_path = processor._generate_ifc_model()
    ifc_file = ifcopenshell.open(ifc_path)
    
    project = ifc_file.by_type("IfcProject")[0]
    assert project.Name == "Test Project"
    
    # Check organization and author in ownership history
    owner_history = project.OwnerHistory
    assert owner_history.OwningUser.ThePerson.FamilyName == "Test Author"
    assert owner_history.OwningOrganization.Name == "Test Organization"

def test_ifc_geometry_creation(processor_setup):
    """Test that IFC geometry is created correctly from detected elements."""
    processor, _, _ = processor_setup
    
    ifc_path = processor._generate_ifc_model()
    ifc_file = ifcopenshell.open(ifc_path)
    
    # Check walls
    walls = ifc_file.by_type("IfcWall")
    assert len(walls) == 2  # Should match mock_detected_elements
    
    # Check slabs (floor and ceiling)
    slabs = ifc_file.by_type("IfcSlab")
    assert len(slabs) == 2
    
    # Check openings
    openings = ifc_file.by_type("IfcOpeningElement")
    assert len(openings) == 1
    
    # Check spaces/zones
    spaces = ifc_file.by_type("IfcSpace")
    assert len(spaces) == 1

def test_ifc_relationships(processor_setup):
    """Test that IFC relationships between elements are set up correctly."""
    processor, _, _ = processor_setup
    
    ifc_path = processor._generate_ifc_model()
    ifc_file = ifcopenshell.open(ifc_path)
    
    # Get the first wall and its opening
    wall = ifc_file.by_type("IfcWall")[0]
    opening = ifc_file.by_type("IfcOpeningElement")[0]
    
    # Check that the opening is properly related to its wall
    has_openings = ifc_file.by_type("IfcRelVoidsElement")
    assert any(rel.RelatingBuildingElement == wall and rel.RelatedOpeningElement == opening
              for rel in has_openings)
    
    # Check that spaces are properly bounded by walls and slabs
    spaces = ifc_file.by_type("IfcSpace")
    space_boundaries = ifc_file.by_type("IfcRelSpaceBoundary")
    assert len(space_boundaries) > 0  # Should have boundaries for walls and slabs

def test_point_mapping_creation(processor_setup):
    """Test that point mapping JSON is created correctly."""
    processor, _, output_dir = processor_setup
    
    # Generate IFC and point mapping
    processor._generate_ifc_model()
    mapping_path = output_dir / "point_mapping.json"
    
    assert os.path.exists(mapping_path)
    # Add specific checks for mapping content based on your implementation
