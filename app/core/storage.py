import os
import shutil
import logging
from fastapi import UploadFile
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Base directories
JOBS_BASE_DIR = "jobs"
os.makedirs(JOBS_BASE_DIR, exist_ok=True)

# In-memory job store
# For production, consider using Redis or a database
jobs: Dict[str, Dict[str, Any]] = {}


def get_job_input_dir(job_id: str) -> str:
    """Returns the input directory path for a job."""
    return os.path.join(JOBS_BASE_DIR, job_id, "input")


def get_job_input_file_path(job_id: str, filename: str) -> str:
    """Returns the absolute path to a specific file in the job's input directory."""
    return os.path.join(get_job_input_dir(job_id), filename)


def get_job_output_dir(job_id: str) -> str:
    """Returns the output directory path for a job."""
    return os.path.join(JOBS_BASE_DIR, job_id, "output")


def save_upload_file(upload_file: UploadFile, destination: str) -> None:
    """Saves an uploaded file to the specified destination."""
    try:
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
        upload_file.file.close()
