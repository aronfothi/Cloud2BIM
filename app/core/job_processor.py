import asyncio
import logging
import yaml
import os
import json
from typing import Dict, Any
from pathlib import Path
import open3d as o3d

from .storage import jobs, get_job_output_dir, get_job_input_dir
from .cloud2entities import CloudToBimProcessor
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

    try:
        # Update status
        jobs[job_id].update({
            "status": "processing",
            "stage": "Parsing configuration",
            "progress": 10
        })

        # Load configuration
        config_content = job_info["config_content"]
        config_data = yaml.safe_load(config_content)

        # Load point cloud
        logger.info(f"Job {job_id}: Loading point cloud from {point_cloud_filepath}")
        pcd = o3d.io.read_point_cloud(point_cloud_filepath)
        if not pcd or len(pcd.points) == 0:
            raise ValueError("Failed to load point cloud or point cloud is empty")

        # Update status
        jobs[job_id].update({
            "stage": "Segmenting point cloud (walls)",
            "progress": 55
        })

        # Initialize and run Cloud2BIM processor
        processor = CloudToBimProcessor(
            job_id=job_id,
            config_data=config_data,
            output_dir=job_output_dir,
            point_cloud_data=pcd
        )

        # Process the point cloud and generate IFC
        processor.process()

        # Move or copy the generated files to the output directory
        ifc_output = os.path.join(job_output_dir, f"{job_id}_model.ifc")
        point_mapping_output = os.path.join(job_output_dir, "point_mapping.json")

        # Update status for saving results
        jobs[job_id].update({
            "stage": "Saving results",
            "progress": 90
        })

        jobs[job_id].update({
            "status": "completed",
            "stage": "Finished",
            "progress": 100,
            "message": "Conversion successful"
        })
        logger.info(f"Job {job_id}: Processing completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id}: Processing failed: {str(e)}")
        logger.exception("Full traceback:")
        jobs[job_id].update({
            "status": "failed",
            "stage": "Error",
            "progress": 100,
            "message": f"Processing failed: {str(e)}",
            "error": str(e)
        })
