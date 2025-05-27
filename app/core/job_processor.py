import logging
import yaml
import os
import open3d as o3d
import time  # Import time for updated_at

from .storage import jobs, get_job_output_dir, get_job_input_dir
from .cloud2entities import CloudToBimProcessor

logger = logging.getLogger(__name__)


async def process_conversion_job(job_id: str) -> None:
    """Process a point cloud to IFC conversion job using CloudToBimProcessor."""
    job_info = jobs[job_id]
    point_cloud_filepath = job_info["point_cloud_file_path"]
    # Construct config file path using job_id and input directory
    job_input_dir = get_job_input_dir(job_id)
    config_filepath = os.path.join(job_input_dir, f"{job_id}_config.yaml")

    job_output_dir = get_job_output_dir(job_id)

    def update_job_progress(
        stage: str, percentage: int, status: str = "processing", message: str = ""
    ):
        """Helper function to update job progress and timestamp."""
        current_time = time.time()
        progress_details = {
            "percentage": percentage,
            "stage": stage,
            "stage_description": message or stage,
        }
        jobs[job_id].update(
            {
                "status": status,
                "stage": stage,  # Keep top-level stage for quick checks
                "progress": progress_details,
                "message": message or f"{stage} - {percentage}%",
                "updated_at": current_time,
            }
        )
        logger.info(
            f"Job {job_id}: Status - {status}, Stage - {stage}, Progress - {percentage}%, Timestamp: {current_time}"
        )

    try:
        update_job_progress("Parsing configuration", 5, message="Reading job configuration.")

        # Load configuration from file
        if not os.path.exists(config_filepath):
            raise FileNotFoundError(f"Configuration file not found: {config_filepath}")
        with open(config_filepath, "r") as f:
            config_data = yaml.safe_load(f)
        # Store loaded config in job_info if it needs to be accessed by other parts not directly using config_data
        job_info["config_data"] = config_data
        logger.info(f"Job {job_id}: Loaded configuration from {config_filepath}")

        update_job_progress("Loading point cloud", 10, message="Preparing to load point cloud data.")

        # Load point cloud
        logger.info(f"Job {job_id}: Loading point cloud from {point_cloud_filepath}")
        if not os.path.exists(point_cloud_filepath):
            raise FileNotFoundError(f"Point cloud file not found: {point_cloud_filepath}")
        if os.path.getsize(point_cloud_filepath) == 0:
            # This check is crucial as o3d.io.read_point_cloud might not fail clearly on empty files
            raise ValueError(f"Point cloud file is empty: {point_cloud_filepath}")

        pcd = o3d.io.read_point_cloud(point_cloud_filepath)
        # Check if the point cloud object was successfully created and has points
        if not pcd or not pcd.has_points():
            logger.error(
                f"Job {job_id}: Failed to load point cloud or point cloud is empty from {point_cloud_filepath}. PCD object: {pcd}, Has Points: {pcd.has_points() if pcd else 'No PCD object'}"
            )
            raise ValueError("Point cloud file is empty or could not be read by Open3D")
        logger.info(f"Job {job_id}: Successfully loaded point cloud with {len(pcd.points)} points.")

        # Initialize CloudToBimProcessor
        # Pass job_id, config_data, output_dir, the loaded pcd object, and the progress callback
        processor = CloudToBimProcessor(
            job_id=job_id,
            config_data=config_data,
            output_dir=job_output_dir,
            point_cloud_data=pcd,  # Pass the loaded Open3D point cloud object
            update_progress_callback=update_job_progress,  # Pass the callback
        )

        # Process the point cloud and generate IFC
        # The CloudToBimProcessor.process() method is expected to make calls to update_job_progress
        update_job_progress("Starting Cloud2BIM processing", 15, message="Initializing Cloud2BIM core processing.")
        processor.process()

        # If processor.process() completes without raising an exception,
        # it should have set the status to 'completed' and progress to 100%.
        # This is a final check.
        if jobs[job_id]["status"] == "processing":
            update_job_progress("Finalizing", 100, status="completed", message="Conversion process completed successfully.")

        logger.info(f"Job {job_id}: Processing finished. Final status: {jobs[job_id]['status']}")

    except FileNotFoundError as e:
        logger.error(f"Job {job_id}: File error during processing: {str(e)}", exc_info=True)
        # Get current percentage, or default to 0 if progress dict/key doesn't exist
        current_percentage = jobs[job_id].get("progress", {}).get("percentage", 0)
        update_job_progress("Error - File Not Found", current_percentage, status="failed", message=str(e))
    except ValueError as e:
        logger.error(f"Job {job_id}: Value error (e.g., empty file, bad data): {str(e)}", exc_info=True)
        current_percentage = jobs[job_id].get("progress", {}).get("percentage", 0)
        update_job_progress("Error - Invalid Data", current_percentage, status="failed", message=str(e))
    except Exception as e:
        logger.error(f"Job {job_id}: Unexpected error during processing: {str(e)}", exc_info=True)
        current_percentage = jobs[job_id].get("progress", {}).get("percentage", 0)
        update_job_progress("Error - Processing Failed", current_percentage, status="failed", message=f"An unexpected error occurred: {str(e)}")
