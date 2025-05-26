import pytest
import os
import uuid
import yaml
import json
import shutil
from pathlib import Path

from app.core.cloud2entities import CloudToBimProcessor
from app.core.aux_functions import load_config_and_variables

# Define test data paths relative to the tests directory
TESTS_DIR = Path(__file__).parent.parent
DATA_DIR = TESTS_DIR / "data"
SAMPLE_PTX = DATA_DIR / "scan6.ptx"
SAMPLE_CONFIG_YAML = DATA_DIR / "sample_config.yaml"


@pytest.fixture
def job_setup():
    """Sets up a temporary job directory structure for testing."""
    job_id = str(uuid.uuid4())
    base_job_dir = TESTS_DIR / "temp_jobs_testing"
    job_input_dir = base_job_dir / job_id / "input"
    job_output_dir = base_job_dir / job_id / "output"

    os.makedirs(job_input_dir, exist_ok=True)
    os.makedirs(job_output_dir, exist_ok=True)

    test_ptx_path = job_input_dir / SAMPLE_PTX.name
    shutil.copy(SAMPLE_PTX, test_ptx_path)

    with open(SAMPLE_CONFIG_YAML, "r") as f:
        config_data = yaml.safe_load(f)

    temp_config_path_for_loader = job_input_dir / "config.yaml"
    with open(temp_config_path_for_loader, "w") as f:
        yaml.dump(config_data, f)

    loaded_config_params = load_config_and_variables(str(temp_config_path_for_loader))

    yield job_id, test_ptx_path, loaded_config_params, job_input_dir, job_output_dir

    if base_job_dir.exists():
        shutil.rmtree(base_job_dir)


def test_cloud_to_bim_processor_full_run(job_setup):
    """
    Tests the full processing run of CloudToBimProcessor.
    It checks if output files are created.
    """
    job_id, ptx_path, config_params, input_dir, output_dir = job_setup

    # Instantiate the processor
    # The processor's __init__ takes:
    # job_id: str, config_data: dict, input_dir: str, output_dir: str
    # The `config_params` from job_setup is the loaded configuration dictionary.
    processor = CloudToBimProcessor(
        job_id=job_id,
        config_data=config_params,  # Corrected argument name from config_params to config_data
        input_dir=str(input_dir),  # Ensure input_dir is a string if Path was used before
        output_dir=str(output_dir),  # Ensure output_dir is a string
        # point_cloud_filename is not an __init__ param; it's derived or passed to methods
    )

    # The CloudToBimProcessor needs to know which point cloud file to process.
    # This is usually set via config_data (e.g., config_data['ptx_file_path'] or similar)
    # or passed to the process() method, or set as an attribute before calling process().
    # Let's assume it's set via config_data or the processor finds it in input_dir.
    # Based on the CloudToBimProcessor._assign_config_variables, it expects 'ptx_file_path'
    # in the config_data. Let's ensure our test config_params (now config_data) has this.

    # Modify config_data in the test to include the path to the test ptx file
    # This path should be relative to how the processor expects it or an absolute path.
    # The processor's _assign_config_variables uses self.config.get("ptx_file_path")
    # and self.xyz_filenames are constructed with self.input_dir.
    # For a single uploaded file, ptx_file_path is the most direct.
    config_params["ptx_file_path"] = str(ptx_path)  # Add the path to the test ptx file

    # Run the processing
    try:
        processor.process()
    except Exception as e:
        pytest.fail(f"CloudToBimProcessor.process() raised an exception: {e}")

    ifc_filename = config_params.get("ifc", {}).get("ifc_output_file", "model.ifc")
    expected_ifc_path = Path(output_dir) / ifc_filename
    assert expected_ifc_path.exists(), f"IFC file {expected_ifc_path} was not created."
    assert expected_ifc_path.stat().st_size > 0, f"IFC file {expected_ifc_path} is empty."

    expected_mapping_path = Path(output_dir) / "point_mapping.json"

    assert (
        expected_mapping_path.exists()
    ), f"Point mapping file {expected_mapping_path} was not created."
    assert (
        expected_mapping_path.stat().st_size > 0
    ), f"Point mapping file {expected_mapping_path} is empty."

    try:
        with open(expected_mapping_path, "r") as f:
            mapping_data = json.load(f)
        assert isinstance(
            mapping_data, dict
        ), "Point mapping file does not contain valid JSON dictionary."
    except json.JSONDecodeError:
        pytest.fail(f"Point mapping file {expected_mapping_path} is not a valid JSON file.")
    except Exception as e:
        pytest.fail(f"Error reading or validating point mapping JSON: {e}")

    print(f"Test for job {job_id} completed. Outputs are in {output_dir}")
