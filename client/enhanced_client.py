"""
Enhanced client with support for both polling and Server-Sent Events (SSE).
Provides real-time progress updates for better user experience.
"""

import requests
import sseclient  # pip install sseclient-py
import json
import time
import sys
from typing import Optional, Callable
from urllib.parse import urljoin

class ProgressTracker:
    """Enhanced progress tracker with support for multiple update methods"""
    
    def __init__(self, job_id: str, server_url: str, use_sse: bool = True):
        self.job_id = job_id
        self.server_url = server_url.rstrip('/')
        self.use_sse = use_sse
        self.last_percentage = -1
        self.last_stage = ""
        
    def track_progress(self, progress_callback: Optional[Callable] = None) -> dict:
        """
        Track job progress using either SSE or polling.
        
        Args:
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Final job result when completed
        """
        if self.use_sse:
            return self._track_with_sse(progress_callback)
        else:
            return self._track_with_polling(progress_callback)
    
    def _track_with_sse(self, progress_callback: Optional[Callable] = None) -> dict:
        """Track progress using Server-Sent Events"""
        sse_url = f"{self.server_url}/api/stream/{self.job_id}"
        
        try:
            print(f"🔄 Connecting to SSE stream: {sse_url}")
            
            response = requests.get(sse_url, stream=True, headers={'Accept': 'text/event-stream'})
            response.raise_for_status()
            
            client = sseclient.SSEClient(response)
            
            for event in client.events():
                if event.event == 'progress':
                    data = json.loads(event.data)
                    self._handle_progress_update(data, progress_callback)
                    
                elif event.event == 'complete':
                    data = json.loads(event.data)
                    print(f"\\n✅ Job completed with status: {data['final_status']}")
                    return data
                    
                elif event.event == 'error':
                    error_data = json.loads(event.data)
                    print(f"\\n❌ SSE Error: {error_data.get('error', 'Unknown error')}")
                    return {"status": "failed", "error": error_data.get('error')}
                    
        except requests.exceptions.RequestException as e:
            print(f"\\n⚠️ SSE connection failed, falling back to polling: {e}")
            return self._track_with_polling(progress_callback)
        except Exception as e:
            print(f"\\n❌ SSE Error: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _track_with_polling(self, progress_callback: Optional[Callable] = None) -> dict:
        """Track progress using traditional polling"""
        print(f"🔄 Starting progress tracking for job {self.job_id}")
        
        while True:
            try:
                response = requests.get(f"{self.server_url}/status/{self.job_id}")
                response.raise_for_status()
                
                job_status = response.json()
                self._handle_progress_update(job_status, progress_callback)
                
                if job_status["status"] in ["completed", "failed"]:
                    return job_status
                    
                time.sleep(2)  # Poll every 2 seconds
                
            except requests.exceptions.RequestException as e:
                print(f"\\n❌ Error checking status: {e}")
                time.sleep(5)  # Wait longer on error
                continue
    
    def _handle_progress_update(self, data: dict, progress_callback: Optional[Callable] = None):
        """Handle progress update from either SSE or polling"""
        progress = data.get("progress", {})
        performance = data.get("performance", {})
        
        percentage = progress.get("percentage", 0)
        stage = progress.get("stage", "")
        stage_description = progress.get("stage_description", "")
        current_operation = progress.get("current_operation", "")
        processing_speed = progress.get("processing_speed", "")
        estimated_remaining = progress.get("estimated_remaining_seconds")
        
        # Only update display if progress changed
        if percentage != self.last_percentage or stage != self.last_stage:
            self.last_percentage = percentage
            self.last_stage = stage
            
            # Create progress bar
            bar_length = 30
            filled_length = int(bar_length * percentage // 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # Format time estimate
            time_str = ""
            if estimated_remaining is not None and estimated_remaining > 0:
                if estimated_remaining < 60:
                    time_str = f" (~{estimated_remaining}s remaining)"
                else:
                    minutes = estimated_remaining // 60
                    seconds = estimated_remaining % 60
                    time_str = f" (~{minutes}m {seconds}s remaining)"
            
            # Format performance info
            perf_str = ""
            if processing_speed:
                perf_str = f" | {processing_speed}"
            
            # Print progress update
            print(f"\\r{bar} {percentage:3d}% | {stage_description}{time_str}{perf_str}", end="", flush=True)
            
            if current_operation:
                print(f"\\n   → {current_operation}", flush=True)
        
        # Call custom callback if provided
        if progress_callback:
            progress_callback(data)

class EnhancedCloud2BIMClient:
    """Enhanced client with SSE support and better progress tracking"""
    
    def __init__(self, server_url: str = "http://localhost:8000", use_sse: bool = True):
        self.server_url = server_url.rstrip('/')
        self.use_sse = use_sse
        
    def convert_point_cloud(self, point_cloud_path: str, config_path: str, 
                          progress_callback: Optional[Callable] = None) -> dict:
        """
        Convert point cloud with enhanced progress tracking.
        
        Args:
            point_cloud_path: Path to point cloud file
            config_path: Path to YAML configuration file  
            progress_callback: Optional callback for progress updates
            
        Returns:
            Conversion result with job details
        """
        print(f"🚀 Starting Cloud2BIM conversion...")
        print(f"   Point Cloud: {point_cloud_path}")
        print(f"   Config: {config_path}")
        print(f"   Progress Method: {'SSE' if self.use_sse else 'Polling'}")
        print()
        
        # Submit job
        job_id = self._submit_job(point_cloud_path, config_path)
        if not job_id:
            return {"status": "failed", "error": "Failed to submit job"}
        
        print(f"📋 Job ID: {job_id}")
        print()
        
        # Track progress
        tracker = ProgressTracker(job_id, self.server_url, self.use_sse)
        result = tracker.track_progress(progress_callback)
        
        return {"job_id": job_id, **result}
    
    def _submit_job(self, point_cloud_path: str, config_path: str) -> Optional[str]:
        """Submit conversion job to server"""
        try:
            with open(point_cloud_path, 'rb') as pc_file, open(config_path, 'rb') as config_file:
                files = {
                    'point_cloud': (os.path.basename(point_cloud_path), pc_file),
                    'config': (os.path.basename(config_path), config_file)
                }
                
                response = requests.post(f"{self.server_url}/convert", files=files)
                response.raise_for_status()
                
                return response.json().get("job_id")
                
        except Exception as e:
            print(f"❌ Error submitting job: {e}")
            return None

def main():
    """Example usage of enhanced client"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Cloud2BIM Client with SSE support")
    parser.add_argument("point_cloud", help="Path to point cloud file")
    parser.add_argument("config", help="Path to YAML configuration file")
    parser.add_argument("--server", default="http://localhost:8000", help="Server URL")
    parser.add_argument("--polling", action="store_true", help="Use polling instead of SSE")
    parser.add_argument("--output", help="Output directory for results")
    
    args = parser.parse_args()
    
    # Create client
    client = EnhancedCloud2BIMClient(args.server, use_sse=not args.polling)
    
    # Custom progress callback
    def progress_callback(data):
        # You can add custom logic here, e.g., update a GUI
        performance = data.get("performance", {})
        if "memory_usage_mb" in performance:
            # Log memory usage periodically
            pass
    
    # Run conversion
    result = client.convert_point_cloud(args.point_cloud, args.config, progress_callback)
    
    print(f"\\n\\n🏁 Final Result: {result}")

if __name__ == "__main__":
    main()
