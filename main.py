from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from starlette.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import shutil
import os
import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
import yaml
import pathlib
import time

# Import the SSE router
from app.api.sse import router as sse_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cloud2BIM Service",
    description="Async point cloud to IFC BIM model conversion service with real-time progress tracking",
    version="1.0.0"
)

# Add CORS middleware for web client support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include SSE router
app.include_router(sse_router, prefix="/api", tags=["streaming"])

# Supported file formats
SUPPORTED_FORMATS = [".ptx", ".xyz", ".ply"]  # Added .ply format


def validate_file_format(filename: str) -> bool:
    """Validates if the file has a supported extension."""
    return pathlib.Path(filename).suffix.lower() in SUPPORTED_FORMATS


# In-memory store for job statuses
# For production, consider a more robust solution like Redis or a database
jobs: Dict[str, Dict[str, Any]] = {}


# Define Pydantic models
class Job(BaseModel):
    job_id: str
    status: str
    message: Union[str, None] = None
    result_url: Union[str, None] = None
    stage: Union[str, None] = None  # Added stage information
    progress: Union[int, None] = None  # Added progress percentage


class ConversionRequest(BaseModel):
    config_yaml: str  # This will be the content of the YAML file as a string


# --- Helper Functions ---
JOBS_BASE_DIR = os.environ.get("JOBS_DIR", "jobs")  # Base directory for all job-related files, configurable via environment

os.makedirs(JOBS_BASE_DIR, exist_ok=True)  # Ensure base jobs directory exists


def get_job_input_dir(job_id: str) -> str:
    """Returns the input directory for a given job ID."""
    return os.path.join(JOBS_BASE_DIR, job_id, "input")


def get_job_output_dir(job_id: str) -> str:
    """Returns the output directory for a given job ID."""
    return os.path.join(JOBS_BASE_DIR, job_id, "output")


def save_upload_file(upload_file: UploadFile, destination: str) -> None:
    """Saves an uploaded file to the specified destination."""
    try:
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
        upload_file.file.close()


def validate_file_extension(filename: str) -> bool:
    """Validates if the file has a supported extension."""
    return any(filename.lower().endswith(ext) for ext in SUPPORTED_FORMATS)


async def process_conversion_job(
    job_id: str, original_point_cloud_filename: str, config_content_str: str
):
    """
    Processes the point cloud to IFC conversion using the CloudToBimProcessor.
    """
    print(f"[DEBUG] Starting process_conversion_job for {job_id}")
    from app.core.cloud2entities import CloudToBimProcessor
    import open3d as o3d

    job_input_dir = get_job_input_dir(job_id)
    job_output_dir = get_job_output_dir(job_id)

    point_cloud_filepath = os.path.join(job_input_dir, f"{job_id}_{original_point_cloud_filename}")

    jobs[job_id]["status"] = "processing"
    jobs[job_id]["stage"] = "Initializing"
    jobs[job_id]["progress"] = 0
    logger.info(f"Job {job_id}: Started processing for {point_cloud_filepath}")
    print(f"[DEBUG] Job {job_id}: Status set to processing")

    try:
        # Step 1: Parse YAML configuration
        jobs[job_id]["stage"] = "Parsing configuration"
        jobs[job_id]["progress"] = 10
        logger.info(f"Job {job_id}: Parsing YAML configuration.")
        try:
            config_data = yaml.safe_load(config_content_str)
            logger.info(f"Job {job_id}: YAML configuration parsed successfully.")
        except yaml.YAMLError as e:
            logger.error(f"Job {job_id}: Error parsing YAML configuration: {e}")
            raise ValueError(f"Invalid YAML configuration: {e}")

        # Step 2: Load point cloud
        jobs[job_id]["stage"] = "Loading point cloud"
        jobs[job_id]["progress"] = 20
        logger.info(f"Job {job_id}: Loading point cloud from {point_cloud_filepath}.")

        # Load point cloud using Open3D
        point_cloud_data = o3d.io.read_point_cloud(point_cloud_filepath)
        if len(point_cloud_data.points) == 0:
            raise ValueError("Point cloud file is empty or could not be read")

        logger.info(f"Job {job_id}: Point cloud loaded with {len(point_cloud_data.points)} points.")

        # Step 3: Initialize and run CloudToBimProcessor
        jobs[job_id]["stage"] = "Processing point cloud"
        jobs[job_id]["progress"] = 30

        # Update progress during processing
        def update_progress(stage: str, progress: int):
            jobs[job_id]["stage"] = stage
            jobs[job_id]["progress"] = progress
            logger.info(f"Job {job_id}: {stage} - {progress}%")
            print(f"[DEBUG] Progress update: Job {job_id}: {stage} - {progress}%")  # Debug print

        # Create processor instance with progress callback
        processor = CloudToBimProcessor(
            job_id=job_id,
            config_data=config_data,
            output_dir=job_output_dir,
            point_cloud_data=point_cloud_data,
            progress_callback=update_progress,
        )

        # Run the actual processing using the process() method
        processor.process()  # This now handles progress updates internally

        # Check if the output files were created and copy them to the expected names
        generated_ifc_file = os.path.join(job_output_dir, f"{job_id}_model.ifc")
        expected_ifc_file = os.path.join(job_output_dir, "model.ifc")

        generated_mapping_file = os.path.join(job_output_dir, f"{job_id}_point_mapping.json")
        expected_mapping_file = os.path.join(job_output_dir, "point_mapping.json")

        update_progress("Finalizing results", 90)

        # Copy/rename files to expected names for download endpoints
        if os.path.exists(generated_ifc_file):
            if generated_ifc_file != expected_ifc_file:
                shutil.copy2(generated_ifc_file, expected_ifc_file)
            logger.info(f"Job {job_id}: IFC file available at {expected_ifc_file}")
        else:
            raise FileNotFoundError(f"Expected IFC output file not found: {generated_ifc_file}")

        if os.path.exists(generated_mapping_file):
            if generated_mapping_file != expected_mapping_file:
                shutil.copy2(generated_mapping_file, expected_mapping_file)
            logger.info(f"Job {job_id}: Point mapping file available at {expected_mapping_file}")
        else:
            logger.warning(f"Job {job_id}: Point mapping file not found: {generated_mapping_file}")

        # Final update
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["stage"] = "Finished"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Conversion successful."
        logger.info(f"Job {job_id}: Processing completed successfully.")

    except ValueError as ve:  # Catch specific, known errors first
        logger.error(f"Job {job_id}: Validation error during processing: {ve}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["stage"] = jobs[job_id].get("stage", "Unknown")  # Keep last known stage
        jobs[job_id]["progress"] = jobs[job_id].get(
            "progress", 0
        )  # Keep last known progress on error
        jobs[job_id]["message"] = str(ve)
    except Exception as e:
        logger.error(f"Job {job_id}: Unhandled error during processing: {e}", exc_info=True)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["stage"] = jobs[job_id].get("stage", "Unknown")
        jobs[job_id]["progress"] = jobs[job_id].get(
            "progress", 0
        )  # Keep last known progress on error
        jobs[job_id]["message"] = f"An unexpected error occurred: {e}"


# --- API Endpoints ---


@app.get("/")
async def root():
    """Root endpoint providing API information"""
    return {
        "service": "Cloud2BIM Service",
        "version": "1.0.0",
        "description": "Async point cloud to IFC BIM model conversion service with real-time progress tracking",
        "endpoints": {
            "convert": "/convert",
            "status": "/status/{job_id}",
            "results": "/results/{job_id}/model.ifc",
            "point_mapping": "/results/{job_id}/point_mapping.json",
            "stream_progress": "/api/stream/progress/{job_id}",
            "stream_basic": "/api/stream/basic/{job_id}"
        }
    }


@app.post("/convert", response_model=Job, status_code=202)  # Set status_code to 202 Accepted
async def create_conversion_job(
    background_tasks: BackgroundTasks,
    point_cloud_file: UploadFile = File(
        ..., description="Point cloud file (PLY, PTX, or XYZ format)"
    ),
    config_file: UploadFile = File(..., description="YAML configuration file"),
):
    """
    Accepts a point cloud file (PTX/XYZ/PLY) and a YAML configuration file,
    stores them for the job, starts an asynchronous conversion job,
    and returns a job ID with status 202 (Accepted).
    """
    job_id = str(uuid.uuid4())

    # Validate file extensions
    if not validate_file_format(point_cloud_file.filename):
        supported_formats_str = ", ".join(SUPPORTED_FORMATS)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats are: {supported_formats_str}",
        )

    if not config_file.filename.lower().endswith((".yaml", ".yml")):
        raise HTTPException(
            status_code=400, detail="Invalid configuration file type. Must be .yaml or .yml"
        )

    # Create job-specific directories
    job_input_dir = get_job_input_dir(job_id)
    job_output_dir = get_job_output_dir(job_id)
    os.makedirs(job_input_dir, exist_ok=True)
    os.makedirs(job_output_dir, exist_ok=True)

    # Use a secure filename based on job_id and original extension, or just job_id + extension
    # For simplicity, we'll use the original filename prefixed with job_id,
    # but ensure it's sanitized if used directly in paths further.
    # The `save_upload_file` function handles the actual saving.

    # Sanitize filenames (basic example, consider more robust sanitization)
    safe_point_cloud_filename = f"{job_id}_{os.path.basename(point_cloud_file.filename)}"
    # Config file is read into memory, so its disk name is less critical here if not saved long-term
    # safe_config_filename = f"{job_id}_{os.path.basename(config_file.filename)}"

    point_cloud_filepath = os.path.join(job_input_dir, safe_point_cloud_filename)
    # config_filepath = os.path.join(job_input_dir, safe_config_filename) # If we were to save config file

    try:
        # Save uploaded files
        save_upload_file(point_cloud_file, point_cloud_filepath)
        logger.info(f"Job {job_id}: Saved point cloud file to {point_cloud_filepath}")

        # Read config file content
        config_content = await config_file.read()
        config_content_str = config_content.decode("utf-8")
        logger.info(f"Job {job_id}: Read configuration file {config_file.filename}")

    except Exception as e:
        logger.error(f"Error saving uploaded files for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not save uploaded files: {e}")
    finally:
        await point_cloud_file.close()
        await config_file.close()

    # Initialize job status
    jobs[job_id] = {
        "status": "pending",  # As per todo.md, initial status
        "stage": "Queued",
        "progress": 0,  # Initial progress
        "message": "Job received and queued for processing.",
        "point_cloud_file_path": point_cloud_filepath,  # Store the actual path to the saved PTX
        "original_point_cloud_filename": os.path.basename(
            point_cloud_file.filename
        ),  # Store original for reference
        # "config_content": config_content_str # Already stored
    }
    # Add config_content_str to the job entry if it's not already implicitly handled
    # by being passed to process_conversion_job. Let's ensure it's in `jobs[job_id]`.
    jobs[job_id]["config_content"] = config_content_str

    print(f"[DEBUG] Job {job_id} initialized with status: {jobs[job_id]['status']}")

    # Add the processing to background tasks
    # Pass the original filename to be used by process_conversion_job if needed for output naming
    background_tasks.add_task(
        process_conversion_job,
        job_id,
        os.path.basename(point_cloud_file.filename),
        config_content_str,
    )

    print(f"[DEBUG] Background task added for job {job_id}")
    
    # Add a brief delay to allow the client to start polling before processing completes
    import asyncio
    await asyncio.sleep(1)

    # Return 202 Accepted status code as per todo.md
    # The response_model will still be Job, but FastAPI handles the status code.
    # We need to ensure the endpoint decorator allows for 202.
    # By default, FastAPI returns 200 for POST. We might need to adjust this or use Response directly.
    # For now, let's keep it simple and assume the client understands the Job model response.
    # The `todo.md` says "responds with 202 and job ID".
    # We can achieve this by returning a Response object with status_code=202
    # from starlette.responses import JSONResponse
    # return JSONResponse(content=Job(...).dict(), status_code=202)
    # However, using response_model=Job and returning a Job instance is cleaner if 200 is acceptable.
    # Let's stick to response_model=Job for now and address 202 specifically if it becomes a hard requirement.

    return Job(
        job_id=job_id,
        status=jobs[job_id]["status"],
        message=jobs[job_id]["message"],
        stage=jobs[job_id]["stage"],
        progress=jobs[job_id]["progress"],  # Return initial progress
    )


@app.get("/status/{job_id}", response_model=Job)
async def get_job_status(job_id: str):
    """
    Retrieves the status of a conversion job.
    """
    job_info = jobs.get(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")

    return Job(
        job_id=job_id,
        status=job_info["status"],
        message=job_info.get("message"),
        result_url=job_info.get("result_url"),
        stage=job_info.get("stage"),
        progress=job_info.get("progress"),  # Include progress
    )


@app.get("/results/{job_id}/model.ifc")  # Updated path as per todo.md
async def download_ifc_file(job_id: str):  # Parameter is job_id now
    """
    Downloads the resulting IFC model file for a completed job.
    """
    job_info = jobs.get(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_info.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed. Status: {job_info.get('status')}",
        )

    output_dir = get_job_output_dir(job_id)
    # Filename is fixed as "model.ifc" according to todo.md for this endpoint
    filename = "model.ifc"
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        logger.error(
            f"Result file {filepath} not found for job {job_id}, though job is marked completed."
        )
        raise HTTPException(
            status_code=404,
            detail=f"Result file not found for job {job_id}. Please check job status or contact support.",
        )

    return FileResponse(
        path=filepath, filename=filename, media_type="application/vnd.ifc"
    )  # Corrected media type


# Placeholder for /results/{job_id}/point_mapping.json (Task 3.4)
@app.get("/results/{job_id}/point_mapping.json")
async def download_point_mapping_file(job_id: str):
    job_info = jobs.get(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_info.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed. Status: {job_info.get('status')}",
        )

    output_dir = get_job_output_dir(job_id)
    filename = "point_mapping.json"  # As per todo.md
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        # If the job is complete but file doesn't exist, this is an issue.
        logger.error(f"Point mapping file {filepath} not found for completed job {job_id}.")
        raise HTTPException(
            status_code=404,
            detail=f"Point mapping file not found for job {job_id}. The job may have failed to produce this output.",
        )

    return FileResponse(path=filepath, filename=filename, media_type="application/json")


@app.get("/debug/test")
async def debug_test():
    """Debug endpoint to verify our changes are loaded"""
    return {"message": "Progress tracking version is loaded", "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn

    # This is for local development. For production, use a proper ASGI server like Gunicorn with Uvicorn workers.
    uvicorn.run(app, host="0.0.0.0", port=8001)
