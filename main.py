from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from starlette.responses import FileResponse # Added for serving files
from pydantic import BaseModel
import uuid
import shutil
import os
import asyncio
import logging
from typing import Dict, Any
import yaml # For parsing YAML

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__

app = FastAPI(title="Cloud2BIM Service")

# In-memory store for job statuses
# For production, consider a more robust solution like Redis or a database
jobs: Dict[str, Dict[str, Any]] = {}

# Define Pydantic models
class Job(BaseModel):
    job_id: str
    status: str
    message: str | None = None
    result_url: str | None = None
    stage: str | None = None # Added stage information
    progress: int | None = None # Added progress percentage

class ConversionRequest(BaseModel):
    config_yaml: str  # This will be the content of the YAML file as a string

# --- Helper Functions ---
JOBS_BASE_DIR = "jobs" # Base directory for all job-related files

os.makedirs(JOBS_BASE_DIR, exist_ok=True) # Ensure base jobs directory exists

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

async def process_conversion_job(job_id: str, original_ptx_filename: str, config_content_str: str):
    """
    Processes the point cloud to IFC conversion.
    """
    job_input_dir = get_job_input_dir(job_id)
    job_output_dir = get_job_output_dir(job_id)
    
    ptx_filepath = os.path.join(job_input_dir, f"{job_id}_{original_ptx_filename}")

    jobs[job_id]["status"] = "processing"
    jobs[job_id]["stage"] = "Initializing"
    jobs[job_id]["progress"] = 0 # Initial progress
    logger.info(f"Job {job_id}: Started processing for {ptx_filepath}")

    total_steps = 5 # Define total number of major steps for progress calculation
    current_step = 0

    try:
        # Step 1: Parse YAML configuration
        current_step += 1
        jobs[job_id]["stage"] = "Parsing configuration"
        jobs[job_id]["progress"] = int((current_step / total_steps) * 100) - 10 # Simulate partial completion
        logger.info(f"Job {job_id}: Parsing YAML configuration.")
        try:
            config_data = yaml.safe_load(config_content_str)
            logger.info(f"Job {job_id}: YAML configuration parsed successfully.")
        except yaml.YAMLError as e:
            logger.error(f"Job {job_id}: Error parsing YAML configuration: {e}")
            raise ValueError(f"Invalid YAML configuration: {e}")

        await asyncio.sleep(1) # Simulate work
        jobs[job_id]["progress"] = int((current_step / total_steps) * 100)

        # Step 2: Load point cloud
        current_step += 1
        jobs[job_id]["stage"] = "Loading point cloud"
        jobs[job_id]["progress"] = int((current_step / total_steps) * 100) - 10 
        logger.info(f"Job {job_id}: Loading point cloud from {ptx_filepath} (simulated).")
        # Placeholder: actual_ptx_data = open3d.io.read_point_cloud(ptx_filepath)
        await asyncio.sleep(2) # Simulate loading
        jobs[job_id]["progress"] = int((current_step / total_steps) * 100)

        # Step 3: Run Cloud2BIM segmentation 
        # This can be broken down further for more granular progress
        current_step += 1
        jobs[job_id]["stage"] = "Segmenting point cloud (slabs)"
        jobs[job_id]["progress"] = int((current_step / total_steps) * 100) - 15
        logger.info(f"Job {job_id}: Running slab detection (simulated).")
        await asyncio.sleep(2) 
        # Placeholder: slabs = detect_slabs(actual_ptx_data, config_data.get(\'slab_params\'))
        
        jobs[job_id]["stage"] = "Segmenting point cloud (walls)"
        jobs[job_id]["progress"] = int((current_step / total_steps) * 100) - 5
        logger.info(f"Job {job_id}: Running wall detection (simulated).")
        await asyncio.sleep(2)
        # Placeholder: walls = detect_walls(actual_ptx_data, config_data.get(\'wall_params\'))
        jobs[job_id]["progress"] = int((current_step / total_steps) * 100)
        
        # ... (other segmentation steps: openings, zones - each could increment progress)

        # Step 4: Generate IFC model
        current_step += 1
        jobs[job_id]["stage"] = "Generating IFC model"
        jobs[job_id]["progress"] = int((current_step / total_steps) * 100) - 10
        logger.info(f"Job {job_id}: Generating IFC model (simulated).")
        # Placeholder: ifc_file_content = generate_ifc_model(slabs, walls, ...)
        await asyncio.sleep(3)
        jobs[job_id]["progress"] = int((current_step / total_steps) * 100)

        # Step 5: Save IFC file and point_mapping.json
        current_step += 1
        jobs[job_id]["stage"] = "Saving results"
        jobs[job_id]["progress"] = int((current_step / total_steps) * 100) - 10
        
        result_filename_ifc = "model.ifc"
        result_filepath_ifc = os.path.join(job_output_dir, result_filename_ifc)
        logger.info(f"Job {job_id}: Saving IFC model to {result_filepath_ifc} (simulated).")
        with open(result_filepath_ifc, "w") as f:
            f.write(f"IFC-CONTENT-PLACEHOLDER-FOR-JOB-{job_id}")
        
        # Generate and save dummy point_mapping.json
        result_filename_mapping = "point_mapping.json"
        result_filepath_mapping = os.path.join(job_output_dir, result_filename_mapping)
        logger.info(f"Job {job_id}: Saving point mapping to {result_filepath_mapping} (simulated).")
        with open(result_filepath_mapping, "w") as f:
            import json
            # Placeholder for actual mapping data
            dummy_mapping_data = {
                "jobId": job_id,
                "ifcElementMappings": [
                    {"ifcGuid": str(uuid.uuid4()), "pointIndices": [100, 101, 102]},
                    {"ifcGuid": str(uuid.uuid4()), "pointIndices": [200, 201, 202]}
                ]
            }
            json.dump(dummy_mapping_data, f, indent=2)
        await asyncio.sleep(1) # Simulate saving
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["stage"] = "Finished"
        jobs[job_id]["progress"] = 100 # Ensure progress is 100% on completion
        jobs[job_id]["message"] = "Conversion successful."
        jobs[job_id]["result_url"] = f"/results/{job_id}/{result_filename_ifc}" 
        logger.info(f"Job {job_id}: Processing completed. Results: {result_filepath_ifc}, {result_filepath_mapping}")

    except ValueError as ve: # Catch specific, known errors first
        logger.error(f"Job {job_id}: Validation error during processing: {ve}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["stage"] = jobs[job_id].get("stage", "Unknown") # Keep last known stage
        jobs[job_id]["progress"] = jobs[job_id].get("progress", 0) # Keep last known progress on error
        jobs[job_id]["message"] = str(ve)
    except Exception as e:
        logger.error(f"Job {job_id}: Unhandled error during processing: {e}", exc_info=True)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["stage"] = jobs[job_id].get("stage", "Unknown")
        jobs[job_id]["progress"] = jobs[job_id].get("progress", 0) # Keep last known progress on error
        jobs[job_id]["message"] = f"An unexpected error occurred: {e}"

# --- API Endpoints ---

@app.post("/convert", response_model=Job, status_code=202) # Set status_code to 202 Accepted
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
    
    # Validate file types (basic validation)
    if not (ptx_file.filename.endswith((".ptx", ".xyz"))):
        raise HTTPException(status_code=400, detail="Invalid point cloud file type. Must be .ptx or .xyz")
    if not (config_file.filename.endswith((".yaml", ".yml"))):
        raise HTTPException(status_code=400, detail="Invalid configuration file type. Must be .yaml or .yml")

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
    safe_ptx_filename = f"{job_id}_{os.path.basename(ptx_file.filename)}"
    # Config file is read into memory, so its disk name is less critical here if not saved long-term
    # safe_config_filename = f"{job_id}_{os.path.basename(config_file.filename)}"

    ptx_filepath = os.path.join(job_input_dir, safe_ptx_filename)
    # config_filepath = os.path.join(job_input_dir, safe_config_filename) # If we were to save config file

    try:
        # Save uploaded files
        save_upload_file(ptx_file, ptx_filepath)
        logger.info(f"Job {job_id}: Saved point cloud file to {ptx_filepath}")
        
        # Read config file content
        config_content = await config_file.read()
        config_content_str = config_content.decode('utf-8')
        logger.info(f"Job {job_id}: Read configuration file {config_file.filename}")

    except Exception as e:
        logger.error(f"Error saving uploaded files for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not save uploaded files: {e}")
    finally:
        await ptx_file.close()
        await config_file.close()

    # Initialize job status
    jobs[job_id] = {
        "status": "pending", # As per todo.md, initial status
        "stage": "Queued",
        "progress": 0, # Initial progress
        "message": "Job received and queued for processing.",
        "ptx_file_path": ptx_filepath, # Store the actual path to the saved PTX
        "original_ptx_filename": os.path.basename(ptx_file.filename), # Store original for reference
        # "config_content": config_content_str # Already stored
    }
    # Add config_content_str to the job entry if it's not already implicitly handled
    # by being passed to process_conversion_job. Let's ensure it's in `jobs[job_id]`.
    jobs[job_id]["config_content"] = config_content_str


    # Add the processing to background tasks
    # Pass the original filename to be used by process_conversion_job if needed for output naming
    background_tasks.add_task(process_conversion_job, job_id, os.path.basename(ptx_file.filename), config_content_str)

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
        progress=jobs[job_id]["progress"] # Return initial progress
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
        progress=job_info.get("progress") # Include progress
    )

@app.get("/results/{job_id}/model.ifc") # Updated path as per todo.md
async def download_ifc_file(job_id: str): # Parameter is job_id now
    """
    Downloads the resulting IFC model file for a completed job.
    """
    job_info = jobs.get(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_info.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"Job {job_id} is not completed. Status: {job_info.get('status')}")

    output_dir = get_job_output_dir(job_id)
    # Filename is fixed as "model.ifc" according to todo.md for this endpoint
    filename = "model.ifc" 
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        logger.error(f"Result file {filepath} not found for job {job_id}, though job is marked completed.")
        raise HTTPException(status_code=404, detail=f"Result file not found for job {job_id}. Please check job status or contact support.")
    
    return FileResponse(path=filepath, filename=filename, media_type='application/vnd.ifc') # Corrected media type

# Placeholder for /results/{job_id}/point_mapping.json (Task 3.4)
@app.get("/results/{job_id}/point_mapping.json")
async def download_point_mapping_file(job_id: str):
    job_info = jobs.get(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_info.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"Job {job_id} is not completed. Status: {job_info.get('status')}")

    output_dir = get_job_output_dir(job_id)
    filename = "point_mapping.json" # As per todo.md
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        # If the job is complete but file doesn't exist, this is an issue.
        logger.error(f"Point mapping file {filepath} not found for completed job {job_id}.")
        raise HTTPException(status_code=404, detail=f"Point mapping file not found for job {job_id}. The job may have failed to produce this output.")

    return FileResponse(path=filepath, filename=filename, media_type='application/json')


if __name__ == "__main__":
    import uvicorn
    # This is for local development. For production, use a proper ASGI server like Gunicorn with Uvicorn workers.
    uvicorn.run(app, host="0.0.0.0", port=8000)
