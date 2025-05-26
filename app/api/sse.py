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
        self.last_progress = -1
        
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
                current_progress = job.get("progress", {}).get("percentage", 0)
                
                # Only send update if progress changed
                if current_progress != self.last_progress:
                    self.last_progress = current_progress
                    
                    event_data = {
                        "job_id": self.job_id,
                        "status": job.get("status"),
                        "progress": job.get("progress", {}),
                        "performance": job.get("performance", {}),
                        "timestamp": job.get("updated_at")
                    }
                    
                    yield {
                        "event": "progress",
                        "data": json.dumps(event_data)
                    }
                
                # Check if job is completed
                if job.get("status") in ["completed", "failed"]:
                    yield {
                        "event": "complete",
                        "data": json.dumps({
                            "job_id": self.job_id,
                            "final_status": job.get("status"),
                            "result": job.get("result")
                        })
                    }
                    break
                
                # Wait before next check
                await asyncio.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error in SSE stream for job {self.job_id}: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }

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
            current_percentage = job.get("progress", {}).get("percentage", 0)
            
            if current_percentage != last_percentage:
                last_percentage = current_percentage
                yield {
                    "event": "progress",
                    "data": str(current_percentage)
                }
            
            if job.get("status") in ["completed", "failed"]:
                yield {
                    "event": "complete",
                    "data": job.get("status")
                }
                break
                
            await asyncio.sleep(1)
    
    return EventSourceResponse(basic_progress_generator())
