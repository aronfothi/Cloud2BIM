"""
Test initialization and configuration handling of CloudToBimProcessor.
"""
import pytest
import os
import yaml
from pathlib import Path
from app.core.cloud2entities import CloudToBimProcessor

# Constants
TESTS_DIR = Path(__file__).parent.parent.parent
DATA_DIR = TESTS_DIR / "data"
SAMPLE_CONFIG_YAML = DATA_DIR / "sample_config.yaml"

@pytest.fixture
def sample_config():
    """Load sample configuration file."""
    with open(SAMPLE_CONFIG_YAML, 'r') as f:
        return yaml.safe_load(f)

@pytest.fixture
def temp_job_dir(tmp_path):
    """Create temporary job directory structure."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    return tmp_path, input_dir, output_dir

def test_processor_initialization(sample_config, temp_job_dir):
    """Test basic initialization of CloudToBimProcessor."""
    tmp_path, input_dir, output_dir = temp_job_dir
    job_id = "test-job-001"
    
    processor = CloudToBimProcessor(
        job_id=job_id,
        config_data=sample_config,
        input_dir=str(input_dir),
        output_dir=str(output_dir)
    )
    
    assert processor.job_id == job_id
    assert processor.input_dir == str(input_dir)
    assert processor.output_dir == str(output_dir)
    assert processor.config == sample_config

def test_processor_initialization_with_invalid_dirs():
    """Test initialization with invalid directories."""
    job_id = "test-job-002"
    invalid_dir = "/nonexistent/path"
    
    with pytest.raises(ValueError, match="Input directory.*does not exist"):
        CloudToBimProcessor(
            job_id=job_id,
            config_data={},
            input_dir=invalid_dir,
            output_dir="./output"
        )

def test_processor_initialization_with_empty_config(temp_job_dir):
    """Test initialization with empty configuration."""
    tmp_path, input_dir, output_dir = temp_job_dir
    job_id = "test-job-003"
    
    with pytest.raises(ValueError, match="Configuration cannot be empty"):
        CloudToBimProcessor(
            job_id=job_id,
            config_data={},
            input_dir=str(input_dir),
            output_dir=str(output_dir)
        )
