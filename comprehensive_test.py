#!/usr/bin/env python3
"""
Comprehensive test for the Cloud2BIM progress tracking system.
This test demonstrates both SSE and polling approaches for progress monitoring.
"""

import asyncio
import requests
import time
import yaml
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
import sseclient

console = Console()

class ProgressDemo:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_api_connection(self):
        """Test if the API is responsive"""
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                console.print("✅ API connection successful", style="green")
                return True
            else:
                console.print(f"❌ API returned {response.status_code}", style="red")
                return False
        except Exception as e:
            console.print(f"❌ Connection failed: {e}", style="red")
            return False
    
    def submit_test_job(self):
        """Submit a test conversion job"""
        console.print("\n📤 Submitting test conversion job...", style="blue")
        
        # Prepare test files
        point_cloud_path = Path("test_data/scan6.ptx")
        config_path = Path("app/config/config.yaml")
        
        if not point_cloud_path.exists():
            console.print(f"❌ Test file not found: {point_cloud_path}", style="red")
            return None
        
        if not config_path.exists():
            console.print(f"❌ Config file not found: {config_path}", style="red")
            return None
        
        # Read config
        with open(config_path, 'r') as f:
            config_content = f.read()
        
        # Submit job
        try:
            with open(point_cloud_path, 'rb') as pc_file, open(config_path, 'rb') as config_file:
                files = {
                    'point_cloud_file': pc_file,
                    'config_file': config_file
                }
                
                response = self.session.post(
                    f"{self.base_url}/convert",
                    files=files
                )
            
            if response.status_code == 202:  # Updated to expect 202 status code
                job_data = response.json()
                job_id = job_data['job_id']
                console.print(f"✅ Job submitted successfully: {job_id}", style="green")
                return job_id
            else:
                console.print(f"❌ Job submission failed: {response.status_code}", style="red")
                console.print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            console.print(f"❌ Error submitting job: {e}", style="red")
            return None
    
    def monitor_with_sse(self, job_id: str, timeout: int = 60):
        """Monitor job progress using Server-Sent Events"""
        console.print(f"\n📡 Monitoring job {job_id} with SSE...", style="blue")
        
        sse_url = f"{self.base_url}/api/stream/progress/{job_id}"
        
        try:
            # Create SSE client
            response = requests.get(sse_url, stream=True, headers={'Accept': 'text/event-stream'})
            if response.status_code != 200:
                console.print(f"❌ SSE connection failed: {response.status_code}", style="red")
                return False
            
            client = sseclient.SSEClient(response)
            
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task("Processing...", total=100)
                start_time = time.time()
                
                for event in client.events():
                    if time.time() - start_time > timeout:
                        console.print("⏰ SSE monitoring timeout", style="yellow")
                        break
                    
                    if event.data:
                        try:
                            import json
                            data = json.loads(event.data)
                            
                            if event.event == "error":
                                console.print(f"❌ Error: {data.get('error', 'Unknown error')}", style="red")
                                break
                            
                            # Update progress
                            if 'progress' in data:
                                progress_data = data['progress']
                                if isinstance(progress_data, dict) and 'percentage' in progress_data:
                                    percentage = progress_data['percentage']
                                    stage = progress_data.get('stage_description', 'Processing')
                                elif isinstance(progress_data, (int, float)):
                                    # Handle case where progress is just a number
                                    percentage = progress_data
                                    stage = data.get('stage', 'Processing')
                                else:
                                    percentage = 0
                                    stage = data.get('stage', 'Processing')
                                
                                progress.update(task, completed=percentage, description=stage)
                                
                                if percentage >= 100 or data.get('status') == 'completed':
                                    console.print("✅ Job completed!", style="green")
                                    return True
                                elif data.get('status') == 'failed':
                                    console.print("❌ Job failed!", style="red")
                                    return False
                                    
                        except json.JSONDecodeError:
                            console.print(f"⚠️ Invalid JSON in SSE event: {event.data}", style="yellow")
                        except Exception as e:
                            console.print(f"⚠️ Error processing SSE event: {e}", style="yellow")
                            
        except Exception as e:
            console.print(f"❌ SSE monitoring error: {e}", style="red")
            return False
        
        return False
    
    def monitor_with_polling(self, job_id: str, timeout: int = 60):
        """Monitor job progress using polling"""
        console.print(f"\n🔄 Monitoring job {job_id} with polling...", style="blue")
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Processing...", total=100)
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    response = self.session.get(f"{self.base_url}/status/{job_id}")
                    if response.status_code == 200:
                        data = response.json()
                        
                        progress_val = data.get('progress', 0)
                        status = data.get('status', 'unknown')
                        stage = data.get('stage', 'Processing')
                        
                        progress.update(task, completed=progress_val, description=stage)
                        
                        if status == 'completed':
                            console.print("✅ Job completed!", style="green")
                            return True
                        elif status == 'failed':
                            console.print("❌ Job failed!", style="red")
                            return False
                            
                    else:
                        console.print(f"⚠️ Status check failed: {response.status_code}", style="yellow")
                        
                except Exception as e:
                    console.print(f"⚠️ Polling error: {e}", style="yellow")
                
                time.sleep(2)  # Poll every 2 seconds
            
            console.print("⏰ Polling timeout", style="yellow")
            return False
    
    async def run_comprehensive_test(self):
        """Run the complete test suite"""
        console.print("🧪 Cloud2BIM Progress Tracking - Comprehensive Test", style="blue bold")
        
        # Test 1: API Connection
        if not self.test_api_connection():
            return
        
        # Test 2: Submit Job
        job_id = self.submit_test_job()
        if not job_id:
            return
        
        # Test 3: Monitor with SSE
        console.print("\n📊 Testing SSE Progress Monitoring", style="blue bold")
        sse_success = self.monitor_with_sse(job_id, timeout=30)
        
        if not sse_success:
            # Test 4: Fallback to Polling
            console.print("\n📊 Falling back to Polling", style="blue bold")
            polling_success = self.monitor_with_polling(job_id, timeout=30)
            
            if polling_success:
                console.print("\n✅ Polling fallback successful!", style="green")
            else:
                console.print("\n❌ Both SSE and polling failed", style="red")
        else:
            console.print("\n✅ SSE monitoring successful!", style="green")
        
        # Test 5: Check final result
        try:
            response = self.session.get(f"{self.base_url}/status/{job_id}")
            if response.status_code == 200:
                final_status = response.json()
                console.print(f"\n📋 Final Job Status:", style="blue bold")
                console.print(f"   Status: {final_status.get('status')}")
                console.print(f"   Progress: {final_status.get('progress', 0)}%")
                console.print(f"   Message: {final_status.get('message', 'N/A')}")
        except Exception as e:
            console.print(f"⚠️ Could not get final status: {e}", style="yellow")

async def main():
    demo = ProgressDemo()
    await demo.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())
