import asyncio
import logging
import yaml
import os
import json
from typing import Dict, Any
from pathlib import Path # Added Path
import open3d as o3d

from .storage import jobs, get_job_output_dir, get_job_input_dir # Removed get_job_input_file_path
# Removed: from .cloud2entities import detect_elements
# Removed: from .generate_ifc import IFCmodel
from .cloud2entities import CloudToBimProcessor # Added import for the class
from app.core.aux_functions import load_config_and_variables
from app.core.point_cloud import read_point_cloud

logger = logging.getLogger(__name__)

async def process_conversion_job(job_id: str) -> None:
    """Process a point cloud to IFC conversion job using CloudToBimProcessor."""
    job_info = jobs[job_id]
    point_cloud_filepath = job_info["point_cloud_file_path"]
    
    # Get job directories
    job_input_dir = get_job_input_dir(job_id)
    job_output_dir = get_job_output_dir(job_id)

    # Write config to a temporary file
    temp_config_filename = f"{job_id}_config.yaml"
    config_filepath = os.path.join(job_input_dir, temp_config_filename)
    try:
        with open(config_filepath, 'w') as f:
            f.write(job_info["config_content"])
    except Exception as e:
        logger.error(f"Job {job_id}: Failed to write config file: {e}")
        jobs[job_id].update({
            "status": "failed",
            "message": "Failed to write configuration file",
            "error": str(e),
            "progress": 100
        })
        return

    # Initialize job status
    jobs[job_id].update({
        "status": "processing",
        "stage": "Initializing",
        "progress": 0
    })
    logger.info(f"Job {job_id}: Started processing for {point_cloud_filepath} with config {config_filepath}")

    try:
        # Load and validate configuration
        config_params = load_config_and_variables(config_path=config_filepath)
        if config_params is None:
            raise ValueError("Failed to load or parse configuration content")

        # Update config with the job_id
        config_params.update({
            "job_id": job_id
        })
        
        # Load point cloud data directly
        jobs[job_id].update({
            "stage": "Loading Point Cloud",
            "progress": 5
        })
        
        # Load the point cloud from file
        pcd = read_point_cloud(point_cloud_filepath)
        if pcd is None:
            raise ValueError(f"Failed to load point cloud from {point_cloud_filepath}")

        # Initialize processor with the loaded point cloud data
        processor = CloudToBimProcessor(
            job_id=job_id,
            config_data=config_params,
            input_dir=job_input_dir,
            output_dir=job_output_dir,
            point_cloud_data=pcd
        )

        # Run processing in a thread to avoid blocking
        jobs[job_id].update({
            "stage": "Processing Point Cloud",
            "progress": 10
        })
        await asyncio.to_thread(processor.process)

        # Check output files
        expected_ifc = os.path.join(job_output_dir, f"{job_id}_model.ifc")
        expected_mapping = os.path.join(job_output_dir, f"{job_id}_point_mapping.json")

        if not os.path.exists(expected_ifc):
            raise FileNotFoundError(f"Expected IFC file not generated: {expected_ifc}")

        # Update job status to completed
        jobs[job_id].update({
            "status": "completed",
            "stage": "Completed",
            "progress": 100,
            "message": "Processing completed successfully",
            "result_files": {
                "model.ifc": expected_ifc,
                "point_mapping.json": expected_mapping if os.path.exists(expected_mapping) else None
            }
        })
        logger.info(f"Job {job_id}: Processing completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id}: Processing failed: {str(e)}")
        jobs[job_id].update({
            "status": "failed",
            "stage": "Failed",
            "progress": 100,
            "message": f"Processing failed: {str(e)}",
            "error": str(e)
        })
    finally:
        # Clean up temporary config file
        if os.path.exists(config_filepath):
            try:
                os.remove(config_filepath)
                logger.info(f"Job {job_id}: Cleaned up temporary config file {config_filepath}")
            except OSError as e_os:
                logger.warning(f"Job {job_id}: Could not remove temporary config file {config_filepath}: {e_os}")

# Helper function for progress updates (optional, if processor doesn't update `jobs` directly)
# def update_job_progress(job_id: str, stage: str, progress: int, message: str):
#     if job_id in jobs:
#         jobs[job_id]["stage"] = stage
#         jobs[job_id]["progress"] = progress
#         jobs[job_id]["message"] = message
#         logger.info(f"Job {job_id} Progress: Stage={stage}, Progress={progress}%, Msg={message}")
