from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration for better type safety"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStage(str, Enum):
    """Processing stage enumeration"""

    INITIALIZING = "initializing"
    LOADING_POINT_CLOUD = "loading_point_cloud"
    PREPROCESSING = "preprocessing"
    DETECTING_SLABS = "detecting_slabs"
    DETECTING_WALLS = "detecting_walls"
    DETECTING_OPENINGS = "detecting_openings"
    DETECTING_ZONES = "detecting_zones"
    GENERATING_IFC = "generating_ifc"
    FINALIZING = "finalizing"


class ProgressInfo(BaseModel):
    """Detailed progress information"""

    percentage: int = Field(default=0, ge=0, le=100)
    stage: ProcessingStage = ProcessingStage.INITIALIZING
    stage_description: str = Field(default="Initializing...")
    current_operation: Optional[str] = None
    processed_items: int = Field(default=0)
    total_items: int = Field(default=0)
    estimated_remaining_seconds: Optional[int] = None
    processing_speed: Optional[str] = None  # e.g., "1.2 points/sec"


class PerformanceMetrics(BaseModel):
    """Performance and resource usage metrics"""

    start_time: datetime
    last_update_time: datetime
    points_processed: int = Field(default=0)
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None


class Job(BaseModel):
    """Enhanced job model with detailed progress tracking"""

    job_id: str
    status: JobStatus
    message: Optional[str] = None
    result_url: Optional[str] = None
    stage: Optional[str] = None
    progress: ProgressInfo = Field(default_factory=ProgressInfo)
    performance: PerformanceMetrics
    error_details: Optional[Dict[str, Any]] = None


class ConversionRequest(BaseModel):
    """Model representing the conversion request configuration."""

    config_yaml: str  # YAML configuration content as string
