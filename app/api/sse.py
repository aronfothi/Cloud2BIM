"""
Server-Sent Events (SSE) implementation for real-time progress updates.
Provides streaming progress updates as an alternative to polling.
"""

import asyncio
import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Store active SSE connections by job_id
active_connections: Dict[str, list] = {}

def get_jobs_store() -> Dict[str, Dict[str, Any]]:
    """Dependency to get the jobs store from main module"""
    import main
    return main.jobs

class SSEProgressStreamer:
    """Manages Server-Sent Events for progress streaming"""
    
    def __init__(self, job_id: str, jobs_store: Dict[str, Dict[str, Any]]):
        self.job_id = job_id
        self.jobs = jobs_store
        self.last_progress_percentage = -1 # Track the percentage specifically
        
    async def stream_progress(self, request: Request):
        """Generator function for SSE progress streaming"""
        logger.info(f"Starting SSE stream for job {self.job_id}")
        
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info(f"SSE client disconnected for job {self.job_id}")
                    break
                
                # Get current job status
                if self.job_id not in self.jobs:
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": "Job not found"})
                    }
                    break
                
                job = self.jobs[self.job_id]
                
                # Safely access progress details
                progress_info = job.get("progress", {})
                current_progress_percentage = progress_info.get("percentage", 0) if isinstance(progress_info, dict) else 0
                
                if current_progress_percentage != self.last_progress_percentage:
                    self.last_progress_percentage = current_progress_percentage
                    
                    # Ensure all parts of event_data are safely accessed
                    performance_data = job.get("performance")
                    event_data = {
                        "job_id": self.job_id,
                        "status": job.get("status"),
                        "progress": progress_info if isinstance(progress_info, dict) else {"percentage": current_progress_percentage, "stage": "unknown"},
                        "performance": performance_data if isinstance(performance_data, dict) else {},
                        "timestamp": job.get("updated_at")
                    }
                    
                    yield {
                        "event": "progress",
                        "data": json.dumps(event_data)
                    }
                
                job_status = job.get("status")
                if job_status in ["completed", "failed"]:
                    result_info = job.get("result")
                    yield {
                        "event": "complete",
                        "data": json.dumps({
                            "job_id": self.job_id,
                            "final_status": job_status,
                            "result": result_info if isinstance(result_info, dict) else {"message": str(result_info)}
                        })
                    }
                    break
                
                # Wait before next check
                await asyncio.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error in SSE stream for job {self.job_id}: {e}", exc_info=True)
            try:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)})
                }
            except Exception as ex_inner: # Handle cases where yielding itself might fail
                logger.error(f"Critical error in SSE stream for job {self.job_id} while reporting error: {ex_inner}", exc_info=True)


@router.get("/stream/progress/{job_id}")
async def stream_job_progress(job_id: str, request: Request, jobs_store: Dict[str, Dict[str, Any]] = Depends(get_jobs_store)):
    """
    SSE endpoint for real-time job progress streaming.
    
    Usage:
    ```javascript
    const eventSource = new EventSource('/api/stream/progress/{job_id}');
    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log('Progress:', data.progress.percentage);
    };
    ```
    """
    if job_id not in jobs_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    streamer = SSEProgressStreamer(job_id, jobs_store)
    return EventSourceResponse(
        streamer.stream_progress(request),
        ping=30,  # Send ping every 30 seconds to keep connection alive
        ping_message_factory=lambda: "ping"
    )

@router.get("/stream/basic/{job_id}")
async def stream_basic_progress(job_id: str, request: Request, jobs_store: Dict[str, Dict[str, Any]] = Depends(get_jobs_store)):
    """
    Simplified SSE endpoint that only sends percentage updates.
    Useful for simple progress bars.
    """
    if job_id not in jobs_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    async def basic_progress_generator():
        last_percentage = -1
        
        while True:
            if await request.is_disconnected():
                break
                
            if job_id not in jobs_store:
                yield {"event": "error", "data": "Job not found"}
                break
            
            job = jobs_store[job_id]
            # Safely access progress percentage
            progress_info = job.get("progress", {})
            current_percentage = progress_info.get("percentage", 0) if isinstance(progress_info, dict) else 0
            
            if current_percentage != last_percentage:
                last_percentage = current_percentage
                yield {
                    "event": "progress",
                    "data": str(current_percentage) # Basic stream sends only percentage as string
                }
            
            job_status = job.get("status")
            if job_status in ["completed", "failed"]:
                yield {
                    "event": "complete",
                    "data": job_status # Basic stream sends final status as string
                }
                break
                
            await asyncio.sleep(1)
    
    return EventSourceResponse(basic_progress_generator())
