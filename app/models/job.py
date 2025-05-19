from pydantic import BaseModel
from typing import Optional

class Job(BaseModel):
    """Model representing a conversion job and its status."""
    job_id: str
    status: str
    message: Optional[str] = None
    result_url: Optional[str] = None
    stage: Optional[str] = None
    progress: Optional[int] = None

class ConversionRequest(BaseModel):
    """Model representing the conversion request configuration."""
    config_yaml: str  # YAML configuration content as string
