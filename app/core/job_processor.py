import asyncio
import logging
import yaml
import os
import json
from typing import Dict, Any
from pathlib import Path # Added Path

from .storage import jobs, get_job_output_dir, get_job_input_dir # Removed get_job_input_file_path
# Removed: from .cloud2entities import detect_elements
# Removed: from .generate_ifc import IFCmodel
from .cloud2entities import CloudToBimProcessor # Added import for the class
from app.core.aux_functions import load_config_and_variables

logger = logging.getLogger(__name__)

async def process_conversion_job(job_id: str) -> None:
    """
    Process a point cloud to IFC conversion job using CloudToBimProcessor.
    Updates job status and progress throughout processing.
    """
    job_info = jobs[job_id]
    # The point_cloud_file_path is now directly stored in job_info by endpoints.py
    point_cloud_filepath_str = job_info["point_cloud_file_path"]
    point_cloud_filename = os.path.basename(point_cloud_filepath_str)
    
    job_input_dir = get_job_input_dir(job_id)
    job_output_dir = get_job_output_dir(job_id)

    # Config content is in job_info, write it to a temporary file for load_config_and_variables
    temp_config_filename = f"{job_id}_config.yaml"
    config_filepath = os.path.join(job_input_dir, temp_config_filename)
    try:
        with open(config_filepath, 'w') as f:
            f.write(job_info["config_content"])
    except Exception as e:
        logger.error(f"Job {job_id}: Failed to write temporary config file {config_filepath}: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = "Failed to process configuration before starting job."
        jobs[job_id]["error"] = str(e) # Add error field
        jobs[job_id]["progress"] = 100
        return

    jobs[job_id]["status"] = "processing"
    jobs[job_id]["stage"] = "Initializing"
    jobs[job_id]["progress"] = 0
    logger.info(f"Job {job_id}: Started processing for {point_cloud_filepath_str} with config {config_filepath}")

    try:
        # Step 1: Load YAML configuration
        jobs[job_id]["stage"] = "Loading configuration"
        jobs[job_id]["progress"] = 5
        
        config_params = load_config_and_variables(config_path=config_filepath)
        if config_params is None:
            logger.error(f"Job {job_id}: Failed to load configuration from {config_filepath}")
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["message"] = f"Failed to load or parse configuration content."
            jobs[job_id]["error"] = "Configuration loading failed."
            jobs[job_id]["progress"] = 100
            return

        logger.info(f"Job {job_id}: Configuration loaded successfully from {config_filepath}")
        jobs[job_id]["progress"] = 10

        # Step 2: Instantiate and run the CloudToBimProcessor
        # The processor will handle its own progress updates internally if designed to do so.
        # For now, we'll update progress around its main call.
        
        processor = CloudToBimProcessor(
            job_id=job_id,
            config_params=config_params,
            input_dir=Path(job_input_dir),
            output_dir=Path(job_output_dir),
            point_cloud_filename=point_cloud_filename # Pass the actual filename
        )

        # Update job status before calling process, which can be long
        jobs[job_id]["stage"] = "Point Cloud Processing"
        jobs[job_id]["progress"] = 15 # Initial progress for the main processing step

        # The CloudToBimProcessor.process() method should encapsulate all steps:
        # - Loading point cloud
        # - Slab detection
        # - Wall and opening detection
        # - Zone identification (if implemented)
        # - IFC generation
        # It should also handle internal logging and potentially progress updates via a callback or by updating job_info directly.
        # For now, we assume it runs to completion or throws an error.
        
        # We can pass the jobs dictionary or a specific job_info reference to the processor
        # if we want it to update progress directly. This is a more advanced pattern.
        # processor.set_progress_updater(lambda stage, progress, message: update_job_progress(job_id, stage, progress, message))
        
        await asyncio.to_thread(processor.process) # Run the synchronous process method in a thread

        # After processor.process() completes, check its outcome if it sets status itself,
        # or assume success if no exception was raised.
        # For now, we assume if it returns without error, it was successful internally.
        # The processor should ideally update the job status to completed/failed itself.
        # If not, we do it here based on lack of exceptions.

        # Check if the processor set a failed status (if it has that capability)
        if jobs[job_id]["status"] == "failed": # If processor updated status to failed
            logger.error(f"Job {job_id}: CloudToBimProcessor reported failure. Message: {jobs[job_id].get('message')}")
            # Progress and message should have been set by the processor or its sub-methods
            if jobs[job_id].get("progress", 0) < 100:
                 jobs[job_id]["progress"] = 100 # Ensure progress is 100 on failure
            return

        # If no exception and processor didn't mark as failed, assume success.
        # The processor should create all necessary output files.
        ifc_output_filename = config_params.get("ifc", {}).get("ifc_output_file", "model.ifc")
        ifc_model_path = os.path.join(job_output_dir, ifc_output_filename)
        mapping_filepath = os.path.join(job_output_dir, "point_mapping.json")

        if not os.path.exists(ifc_model_path):
            logger.error(f"Job {job_id}: IFC file not found at {ifc_model_path} after processing.")
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["message"] = "Processing completed but output IFC file is missing."
            jobs[job_id]["error"] = "Output IFC file not found."
            jobs[job_id]["progress"] = 100
            return

        if not os.path.exists(mapping_filepath):
            logger.warning(f"Job {job_id}: Point mapping file not found at {mapping_filepath}. Creating empty fallback.")
            # This case should ideally be handled by the processor ensuring it always creates one.
            with open(mapping_filepath, "w") as f:
                json.dump({}, f, indent=2)
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["stage"] = "Finished"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Conversion successful. Output files generated."
        logger.info(f"Job {job_id}: Processing completed successfully by CloudToBimProcessor.")

    except Exception as e:
        logger.error(f"Job {job_id}: Error during CloudToBimProcessor execution: {str(e)}", exc_info=True)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Error during processing: {str(e)}"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["progress"] = 100
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
