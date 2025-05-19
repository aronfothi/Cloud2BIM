from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from starlette.responses import FileResponse
from app.models.job import Job
from app.core.job_processor import process_conversion_job
from app.core.storage import (
    get_job_input_dir,
    get_job_output_dir,
    save_upload_file,
    jobs
)
import uuid
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/convert", response_model=Job, status_code=202)
async def create_conversion_job(
    background_tasks: BackgroundTasks,
    ptx_file: UploadFile = File(..., description="PTX or XYZ point cloud file"),
    config_file: UploadFile = File(..., description="YAML configuration file")
):
    """
    Accepts a point cloud file (PTX/XYZ) and a YAML configuration file,
    stores them for the job, starts an asynchronous conversion job, 
    and returns a job ID with status 202 (Accepted).
    """
    job_id = str(uuid.uuid4())
    
    # Validate file types
    if not (ptx_file.filename.endswith((".ptx", ".xyz"))):
        raise HTTPException(status_code=400, detail="Invalid point cloud file type. Must be .ptx or .xyz")
    if not (config_file.filename.endswith((".yaml", ".yml"))):
        raise HTTPException(status_code=400, detail="Invalid configuration file type. Must be .yaml or .yml")

    # Create job directories
    job_input_dir = get_job_input_dir(job_id)
    job_output_dir = get_job_output_dir(job_id)
    os.makedirs(job_input_dir, exist_ok=True)
    os.makedirs(job_output_dir, exist_ok=True)
    
    # Save files
    safe_ptx_filename = f"{job_id}_{os.path.basename(ptx_file.filename)}"
    ptx_filepath = os.path.join(job_input_dir, safe_ptx_filename)

    try:
        save_upload_file(ptx_file, ptx_filepath)
        logger.info(f"Job {job_id}: Saved point cloud file to {ptx_filepath}")
        
        config_content = await config_file.read()
        config_content_str = config_content.decode('utf-8')
        logger.info(f"Job {job_id}: Read configuration file {config_file.filename}")

    except Exception as e:
        logger.error(f"Error saving uploaded files for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not save uploaded files: {e}")
    finally:
        await ptx_file.close()
        await config_file.close()

    # Initialize job
    jobs[job_id] = {
        "status": "pending",
        "stage": "Queued",
        "progress": 0,
        "message": "Job received and queued for processing.",
        "ptx_file_path": ptx_filepath,
        "original_ptx_filename": os.path.basename(ptx_file.filename),
        "config_content": config_content_str
    }

    background_tasks.add_task(process_conversion_job, job_id)

    return Job(
        job_id=job_id, 
        status=jobs[job_id]["status"], 
        message=jobs[job_id]["message"],
        stage=jobs[job_id]["stage"],
        progress=jobs[job_id]["progress"]
    )

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
        progress=job_info.get("progress")
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
            detail=f"Job {job_id} is not completed. Status: {job_info.get('status')}"
        )

    output_dir = get_job_output_dir(job_id)
    filename = "model.ifc"
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        logger.error(f"Result file {filepath} not found for job {job_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Result file not found for job {job_id}"
        )
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type='application/vnd.ifc'
    )

@router.get("/results/{job_id}/point_mapping.json")
async def download_point_mapping_file(job_id: str):
    """Downloads the point mapping JSON file for a completed job."""
    job_info = jobs.get(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_info.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed. Status: {job_info.get('status')}"
        )

    output_dir = get_job_output_dir(job_id)
    filename = "point_mapping.json"
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        logger.error(f"Point mapping file {filepath} not found for job {job_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Point mapping file not found for job {job_id}"
        )

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type='application/json'
    )
