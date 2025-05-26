from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from starlette.responses import FileResponse
from app.models.job import Job
from app.models.point_cloud import PointCloudData
from app.core.job_processor import process_conversion_job
from app.core.storage import get_job_input_dir, get_job_output_dir, jobs
import uuid
import os
import json
import yaml
import logging
import open3d as o3d

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/convert", response_model=Job, status_code=202)
async def create_conversion_job(
    background_tasks: BackgroundTasks,
    point_cloud_data: UploadFile = File(..., description="JSON file containing point cloud data"),
    config_file: UploadFile = File(..., description="YAML configuration file"),
):
    """
    Accepts point cloud data as a JSON file (containing points and optional colors)
    and a YAML configuration file, stores them for the job, starts an asynchronous
    conversion job, and returns a job ID with status 202 (Accepted).
    """
    job_id = str(uuid.uuid4())

    try:
        # Parse point cloud data
        point_cloud_content = await point_cloud_data.read()
        point_cloud_dict = json.loads(point_cloud_content.decode("utf-8"))
        point_cloud = PointCloudData(**point_cloud_dict)

        # Parse configuration
        config_content = await config_file.read()
        config_data = yaml.safe_load(config_content.decode("utf-8"))

        # Create job directories
        job_input_dir = get_job_input_dir(job_id)
        job_output_dir = get_job_output_dir(job_id)
        os.makedirs(job_input_dir, exist_ok=True)
        os.makedirs(job_output_dir, exist_ok=True)

        # Convert point cloud data to Open3D format and save as PLY
        points_array, colors_array = point_cloud.to_numpy()
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points_array)
        if colors_array is not None:
            pcd.colors = o3d.utility.Vector3dVector(colors_array)

        # Save point cloud in PLY format for processing
        pc_filepath = os.path.join(job_input_dir, f"{job_id}_input.ply")
        o3d.io.write_point_cloud(pc_filepath, pcd)
        logger.info(f"Job {job_id}: Saved point cloud data to {pc_filepath}")

        # Save configuration
        config_filepath = os.path.join(job_input_dir, f"{job_id}_config.yaml")
        with open(config_filepath, "w") as f:
            yaml.dump(config_data, f)
        logger.info(f"Job {job_id}: Saved configuration to {config_filepath}")

        # Initialize job
        jobs[job_id] = {
            "status": "pending",
            "stage": "Queued",
            "progress": 0,
            "message": "Job received and queued for processing.",
            "point_cloud_file_path": pc_filepath,
            "original_point_cloud_filename": point_cloud.filename,
            "config_data": config_data,
        }

        # Start processing
        background_tasks.add_task(process_conversion_job, job_id)

        return Job(
            job_id=job_id,
            status=jobs[job_id]["status"],
            message=jobs[job_id]["message"],
            stage=jobs[job_id]["stage"],
            progress=jobs[job_id]["progress"],
        )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in point cloud data: {e}")
        raise HTTPException(status_code=400, detail="Invalid point cloud data format")
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in configuration: {e}")
        raise HTTPException(status_code=400, detail="Invalid configuration format")
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await point_cloud_data.close()
        await config_file.close()


@router.get("/status/{job_id}", response_model=Job)
async def get_job_status(job_id: str):
    """Retrieves the status of a conversion job."""
    job_info = jobs.get(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")

    return Job(
        job_id=job_id,
        status=job_info["status"],
        message=job_info.get("message"),
        result_url=job_info.get("result_url"),
        stage=job_info.get("stage"),
        progress=job_info.get("progress"),
    )


@router.get("/results/{job_id}/model.ifc")
async def download_ifc_file(job_id: str):
    """Downloads the resulting IFC model file for a completed job."""
    job_info = jobs.get(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_info.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed. Status: {job_info.get('status')}",
        )

    output_dir = get_job_output_dir(job_id)
    filename = "model.ifc"
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        logger.error(f"Result file {filepath} not found for job {job_id}")
        raise HTTPException(status_code=404, detail=f"Result file not found for job {job_id}")

    return FileResponse(path=filepath, filename=filename, media_type="application/vnd.ifc")


@router.get("/results/{job_id}/point_mapping.json")
async def download_point_mapping_file(job_id: str):
    """Downloads the point mapping JSON file for a completed job."""
    job_info = jobs.get(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_info.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed. Status: {job_info.get('status')}",
        )

    output_dir = get_job_output_dir(job_id)
    filename = "point_mapping.json"
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        logger.error(f"Point mapping file {filepath} not found for job {job_id}")
        raise HTTPException(
            status_code=404, detail=f"Point mapping file not found for job {job_id}"
        )

    return FileResponse(path=filepath, filename=filename, media_type="application/json")
