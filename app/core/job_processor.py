import asyncio
import logging
import yaml
import os
import json
import uuid
from typing import Dict, Any
from .storage import jobs, get_job_output_dir

logger = logging.getLogger(__name__)

async def process_conversion_job(job_id: str) -> None:
    """
    Process a point cloud to IFC conversion job.
    Updates job status and progress throughout processing.
    """
    job_info = jobs[job_id]
    ptx_filepath = job_info["ptx_file_path"]
    config_content_str = job_info["config_content"]
    job_output_dir = get_job_output_dir(job_id)

    jobs[job_id]["status"] = "processing"
    jobs[job_id]["stage"] = "Initializing"
    jobs[job_id]["progress"] = 0
    logger.info(f"Job {job_id}: Started processing for {ptx_filepath}")

    total_steps = 5
    current_step = 0

    try:
        # Step 1: Parse YAML configuration
        current_step += 1
        jobs[job_id]["stage"] = "Parsing configuration"
        jobs[job_id]["progress"] = int((current_step / total_steps) * 100) - 10
        
        config_data = yaml.safe_load(config_content_str)
        logger.info(f"Job {job_id}: YAML configuration parsed successfully")
        
        await asyncio.sleep(1)  # Simulate work
        jobs[job_id]["progress"] = int((current_step / total_steps) * 100)

        # TODO: Replace simulation with actual Cloud2BIM processing
        # Placeholder for now - will be implemented in next phase
        await simulate_processing_steps(job_id, current_step, total_steps)
        
        # Save results
        result_filename_ifc = "model.ifc"
        result_filepath_ifc = os.path.join(job_output_dir, result_filename_ifc)
        with open(result_filepath_ifc, "w") as f:
            f.write(f"IFC-CONTENT-PLACEHOLDER-FOR-JOB-{job_id}")
        
        result_filename_mapping = "point_mapping.json"
        result_filepath_mapping = os.path.join(job_output_dir, result_filename_mapping)
        with open(result_filepath_mapping, "w") as f:
            dummy_mapping_data = {
                "jobId": job_id,
                "ifcElementMappings": [
                    {"ifcGuid": str(uuid.uuid4()), "pointIndices": [100, 101, 102]},
                    {"ifcGuid": str(uuid.uuid4()), "pointIndices": [200, 201, 202]}
                ]
            }
            json.dump(dummy_mapping_data, f, indent=2)
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["stage"] = "Finished"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Conversion successful"
        jobs[job_id]["result_url"] = f"/results/{job_id}/{result_filename_ifc}"
        logger.info(f"Job {job_id}: Processing completed successfully")

    except yaml.YAMLError as e:
        logger.error(f"Job {job_id}: Error parsing YAML configuration: {e}")
        set_job_failed(job_id, f"Invalid YAML configuration: {e}")
    except Exception as e:
        logger.error(f"Job {job_id}: Unhandled error during processing: {e}", exc_info=True)
        set_job_failed(job_id, f"An unexpected error occurred: {e}")

async def simulate_processing_steps(job_id: str, current_step: int, total_steps: int) -> None:
    """Simulates the processing steps. Will be replaced with actual Cloud2BIM logic."""
    # Step 2: Load point cloud
    current_step += 1
    jobs[job_id]["stage"] = "Loading point cloud"
    jobs[job_id]["progress"] = int((current_step / total_steps) * 100) - 10
    await asyncio.sleep(2)
    jobs[job_id]["progress"] = int((current_step / total_steps) * 100)

    # Step 3: Segmentation
    current_step += 1
    jobs[job_id]["stage"] = "Segmenting point cloud"
    jobs[job_id]["progress"] = int((current_step / total_steps) * 100) - 15
    await asyncio.sleep(4)
    jobs[job_id]["progress"] = int((current_step / total_steps) * 100)

    # Step 4: IFC Generation
    current_step += 1
    jobs[job_id]["stage"] = "Generating IFC model"
    jobs[job_id]["progress"] = int((current_step / total_steps) * 100) - 10
    await asyncio.sleep(3)
    jobs[job_id]["progress"] = int((current_step / total_steps) * 100)

def set_job_failed(job_id: str, error_message: str) -> None:
    """Updates job status to failed with the given error message."""
    jobs[job_id]["status"] = "failed"
    jobs[job_id]["message"] = error_message
    jobs[job_id]["stage"] = jobs[job_id].get("stage", "Unknown")
    jobs[job_id]["progress"] = jobs[job_id].get("progress", 0)
