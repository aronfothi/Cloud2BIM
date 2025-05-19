import asyncio
import logging
import yaml
import os
import json
import uuid
import open3d as o3d
import numpy as np
from typing import Dict, Any
from .storage import jobs, get_job_output_dir
from .cloud2entities import process_point_cloud, detect_elements
from .generate_ifc import IFCmodel

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

    try:
        # Step 1: Parse YAML configuration
        jobs[job_id]["stage"] = "Parsing configuration"
        jobs[job_id]["progress"] = 10
        config_data = yaml.safe_load(config_content_str)
        logger.info(f"Job {job_id}: YAML configuration parsed successfully")

        # Step 2: Load and preprocess point cloud
        jobs[job_id]["stage"] = "Loading point cloud"
        jobs[job_id]["progress"] = 20
        
        # Load point cloud based on file extension
        if ptx_filepath.endswith('.ptx'):
            pcd = o3d.io.read_point_cloud(ptx_filepath, format='ptx')
        else:  # xyz format
            pcd = o3d.io.read_point_cloud(ptx_filepath, format='xyz')
        
        logger.info(f"Job {job_id}: Point cloud loaded with {len(pcd.points)} points")

        # Step 3: Process point cloud (segment and detect elements)
        jobs[job_id]["stage"] = "Processing point cloud"
        jobs[job_id]["progress"] = 40
        
        # Preprocess: downsample and remove noise
        preprocessed_pcd = process_point_cloud(
            pcd,
            voxel_size=config_data["preprocessing"]["voxel_size"],
            noise_threshold=config_data["preprocessing"]["noise_threshold"]
        )
        
        # Detect building elements
        elements = detect_elements(
            preprocessed_pcd,
            wall_params=config_data["detection"]["wall"],
            slab_params=config_data["detection"]["slab"],
            opening_params=config_data["detection"]["opening"]
        )
        
        jobs[job_id]["progress"] = 60
        logger.info(f"Job {job_id}: Elements detected: {len(elements)} total")

        # Step 4: Generate IFC model
        jobs[job_id]["stage"] = "Generating IFC model"
        jobs[job_id]["progress"] = 80
        
        ifc_model = IFCmodel(
            project_name=config_data["ifc"]["project_name"],
            output_file=os.path.join(job_output_dir, "model.ifc")
        )
        
        # Create IFC elements and store mapping
        point_mapping = {"jobId": job_id, "ifcElementMappings": []}
        
        for element in elements:
            ifc_guid = ifc_model.create_element(
                element_type=element["type"],
                geometry=element["geometry"],
                properties=element["properties"]
            )
            
            point_mapping["ifcElementMappings"].append({
                "ifcGuid": ifc_guid,
                "pointIndices": element["point_indices"]
            })
        
        # Save IFC file
        ifc_model.write()
        logger.info(f"Job {job_id}: IFC model generated successfully")

        # Save point mapping
        mapping_filepath = os.path.join(job_output_dir, "point_mapping.json")
        with open(mapping_filepath, "w") as f:
            json.dump(point_mapping, f, indent=2)
        
        # Update job status
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["stage"] = "Finished"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Conversion successful"
        logger.info(f"Job {job_id}: Processing completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id}: Error during processing: {str(e)}", exc_info=True)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Error during processing: {str(e)}"
        raise
