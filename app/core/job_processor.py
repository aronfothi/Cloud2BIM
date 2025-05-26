import logging
import yaml
import os
import open3d as o3d

from .storage import jobs, get_job_output_dir, get_job_input_dir
from .cloud2entities import CloudToBimProcessor

logger = logging.getLogger(__name__)


async def process_conversion_job(job_id: str) -> None:
    """Process a point cloud to IFC conversion job using CloudToBimProcessor."""
    job_info = jobs[job_id]
    point_cloud_filepath = job_info["point_cloud_file_path"]

    # Get job directories
    _ = get_job_input_dir(job_id)  # job_input_dir not used but kept for future functionality
    job_output_dir = get_job_output_dir(job_id)

    try:
        # Update status
        jobs[job_id].update(
            {"status": "processing", "stage": "Parsing configuration", "progress": 10}
        )

        # Load configuration
        config_content = job_info["config_content"]
        config_data = yaml.safe_load(config_content)

        # Load point cloud
        logger.info(f"Job {job_id}: Loading point cloud from {point_cloud_filepath}")
        pcd = o3d.io.read_point_cloud(point_cloud_filepath)
        if not pcd or len(pcd.points) == 0:
            raise ValueError("Failed to load point cloud or point cloud is empty")

        # Update status
        jobs[job_id].update({"stage": "Segmenting point cloud (walls)", "progress": 55})

        # Initialize and run Cloud2BIM processor
        processor = CloudToBimProcessor(
            job_id=job_id, config_data=config_data, output_dir=job_output_dir, point_cloud_data=pcd
        )

        # Process the point cloud and generate IFC
        processor.process()

        # Process the point cloud and generate IFC
        processor.process()

        # Define output paths (files are created by processor.process())
        _ = os.path.join(job_output_dir, f"{job_id}_model.ifc")  # ifc_output for future use
        _ = os.path.join(job_output_dir, "point_mapping.json")  # point_mapping_output for future use

        # Update status for saving results
        jobs[job_id].update({"stage": "Saving results", "progress": 90})

        jobs[job_id].update(
            {
                "status": "completed",
                "stage": "Finished",
                "progress": 100,
                "message": "Conversion successful",
            }
        )
        logger.info(f"Job {job_id}: Processing completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id}: Processing failed: {str(e)}")
        logger.exception("Full traceback:")
        jobs[job_id].update(
            {
                "status": "failed",
                "stage": "Error",
                "progress": 100,
                "message": f"Processing failed: {str(e)}",
                "error": str(e),
            }
        )
