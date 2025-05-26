#!/usr/bin/env python3
"""
Enhanced Cloud2BIM Client with Progress Tracking
Combines the original client's PTX processing with new progress tracking features.
"""

import time
import os
import requests
import numpy as np
import open3d as o3d
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, MofNCompleteColumn
from rich.panel import Panel
from rich.table import Table
import sseclient
import json
from typing import Optional, List, Dict, Any

console = Console()

class EnhancedProgressClient:
    """Enhanced Cloud2BIM client with PTX processing and progress tracking"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def read_custom_ptx(self, ptx_file_path: str) -> np.ndarray:
        """
        Read PTX file and return point cloud as numpy array.
        Based on the original client's implementation.
        """
        console.print(f"📖 Reading PTX file: {ptx_file_path}", style="blue")
        
        points = []
        with open(ptx_file_path, 'r') as file:
            lines = file.readlines()
        
        # Parse PTX header if present
        header_lines = 0
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'):
                header_lines += 1
                continue
            
            # Try to parse as point data
            try:
                parts = line.split()
                if len(parts) >= 3:
                    x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                    points.append([x, y, z])
            except ValueError:
                if i < 10:  # Assume first few lines might be header
                    header_lines += 1
                    continue
                break
        
        points_array = np.array(points)
        console.print(f"✅ Loaded {len(points_array)} points from PTX file", style="green")
        return points_array
    
    def convert_to_ply(self, points: np.ndarray, output_path: str) -> bool:
        """Convert numpy points to PLY file using Open3D"""
        console.print(f"🔄 Converting to PLY format...", style="blue")
        
        try:
            # Create Open3D point cloud
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(points)
            
            # Save as PLY
            success = o3d.io.write_point_cloud(output_path, pcd)
            
            if success:
                file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
                console.print(f"✅ PLY file saved: {output_path} ({file_size:.2f} MB)", style="green")
                return True
            else:
                console.print(f"❌ Failed to save PLY file", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ Error converting to PLY: {e}", style="red")
            return False
    
    def process_ptx_files(self, ptx_files: List[str], output_ply: str) -> bool:
        """Process one or more PTX files and create a merged PLY file"""
        console.print(f"\n🔧 Processing {len(ptx_files)} PTX file(s)...", style="blue bold")
        
        all_points = []
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Processing PTX files", total=len(ptx_files))
            
            for i, ptx_file in enumerate(ptx_files):
                progress.update(task, description=f"Reading {Path(ptx_file).name}")
                
                if not os.path.exists(ptx_file):
                    console.print(f"❌ File not found: {ptx_file}", style="red")
                    return False
                
                points = self.read_custom_ptx(ptx_file)
                if len(points) > 0:
                    all_points.append(points)
                
                progress.advance(task)
        
        if not all_points:
            console.print("❌ No valid points found in PTX files", style="red")
            return False
        
        # Merge all points
        console.print(f"🔗 Merging point clouds...", style="blue")
        merged_points = np.vstack(all_points)
        
        total_points = len(merged_points)
        console.print(f"📊 Total points after merging: {total_points:,}", style="green")
        
        # Convert to PLY
        return self.convert_to_ply(merged_points, output_ply)
    
    def submit_job(self, ply_file: str, config_file: str) -> Optional[str]:
        """Submit conversion job to the server"""
        console.print(f"\n📤 Submitting job to Cloud2BIM service...", style="blue")
        
        try:
            with open(ply_file, 'rb') as pf, open(config_file, 'rb') as cf:
                files = {
                    'point_cloud_file': (os.path.basename(ply_file), pf, 'application/octet-stream'),
                    'config_file': (os.path.basename(config_file), cf, 'text/yaml')
                }
                
                response = self.session.post(f"{self.base_url}/convert", files=files)
                
                if response.status_code == 202:
                    job_data = response.json()
                    job_id = job_data['job_id']
                    console.print(f"✅ Job submitted successfully!", style="green")
                    console.print(f"   Job ID: {job_id}")
                    return job_id
                else:
                    console.print(f"❌ Job submission failed: {response.status_code}", style="red")
                    console.print(f"   Response: {response.text}")
                    return None
                    
        except Exception as e:
            console.print(f"❌ Error submitting job: {e}", style="red")
            return None
    
    def monitor_with_sse(self, job_id: str) -> bool:
        """Monitor job progress using Server-Sent Events"""
        console.print(f"\n📡 Monitoring progress with SSE...", style="blue")
        
        sse_url = f"{self.base_url}/api/stream/progress/{job_id}"
        
        try:
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
                
                task = progress.add_task("Processing point cloud", total=100)
                
                for event in client.events():
                    if event.data:
                        try:
                            data = json.loads(event.data)
                            
                            if event.event == "error":
                                console.print(f"❌ Error: {data.get('error', 'Unknown error')}", style="red")
                                return False
                            
                            # Handle progress updates
                            if 'progress' in data:
                                progress_info = data['progress']
                                
                                # Handle both old format (integer) and new format (dict)
                                if isinstance(progress_info, dict):
                                    percentage = progress_info.get('percentage', 0)
                                    stage = progress_info.get('stage_description', 'Processing')
                                    
                                    # Show performance info if available
                                    if 'performance' in data:
                                        perf = data['performance']
                                        cpu = perf.get('cpu_percent', 0)
                                        memory = perf.get('memory_percent', 0)
                                        stage += f" (CPU: {cpu:.1f}%, Mem: {memory:.1f}%)"
                                        
                                else:
                                    percentage = progress_info
                                    stage = "Processing"
                                
                                progress.update(task, completed=percentage, description=stage)
                                
                                # Check completion status
                                status = data.get('status', '')
                                if percentage >= 100 or status == 'completed':
                                    console.print("✅ Job completed successfully!", style="green")
                                    return True
                                elif status == 'failed':
                                    console.print("❌ Job failed!", style="red")
                                    return False
                                    
                        except json.JSONDecodeError:
                            console.print(f"⚠️ Invalid JSON in SSE event", style="yellow")
                        except Exception as e:
                            console.print(f"⚠️ Error processing SSE event: {e}", style="yellow")
                            
        except Exception as e:
            console.print(f"❌ SSE monitoring error: {e}", style="red")
            return False
        
        return False
    
    def monitor_with_polling(self, job_id: str) -> bool:
        """Monitor job progress using polling (fallback method)"""
        console.print(f"\n🔄 Monitoring progress with polling...", style="blue")
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Processing point cloud", total=100)
            
            while True:
                try:
                    response = self.session.get(f"{self.base_url}/status/{job_id}")
                    if response.status_code == 200:
                        data = response.json()
                        
                        progress_val = data.get('progress', 0)
                        status = data.get('status', 'unknown')
                        stage = data.get('stage', 'Processing')
                        
                        progress.update(task, completed=progress_val, description=stage)
                        
                        if status == 'completed':
                            console.print("✅ Job completed successfully!", style="green")
                            return True
                        elif status == 'failed':
                            console.print(f"❌ Job failed: {data.get('message', 'Unknown error')}", style="red")
                            return False
                            
                    else:
                        console.print(f"⚠️ Status check failed: {response.status_code}", style="yellow")
                        
                except Exception as e:
                    console.print(f"⚠️ Polling error: {e}", style="yellow")
                
                time.sleep(2)  # Poll every 2 seconds
    
    def download_results(self, job_id: str, output_dir: str = "results") -> bool:
        """Download the results from completed job"""
        console.print(f"\n⬇️ Downloading results...", style="blue")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Download IFC file
        ifc_url = f"{self.base_url}/results/{job_id}/model.ifc"
        ifc_path = os.path.join(output_dir, f"{job_id}_model.ifc")
        
        try:
            response = self.session.get(ifc_url)
            if response.status_code == 200:
                with open(ifc_path, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content) / 1024  # KB
                console.print(f"✅ IFC model downloaded: {ifc_path} ({file_size:.1f} KB)", style="green")
            else:
                console.print(f"❌ Failed to download IFC: {response.status_code}", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ Error downloading IFC: {e}", style="red")
            return False
        
        # Download point mapping (optional)
        mapping_url = f"{self.base_url}/results/{job_id}/point_mapping.json"
        mapping_path = os.path.join(output_dir, f"{job_id}_mapping.json")
        
        try:
            response = self.session.get(mapping_url)
            if response.status_code == 200:
                with open(mapping_path, 'w') as f:
                    f.write(response.text)
                console.print(f"✅ Point mapping downloaded: {mapping_path}", style="green")
        except Exception as e:
            console.print(f"⚠️ Point mapping not available: {e}", style="yellow")
        
        return True
    
    def process_and_convert(self, ptx_files: List[str], config_file: str, use_sse: bool = True) -> bool:
        """Complete workflow: PTX processing -> conversion -> monitoring -> download"""
        
        console.print("🚀 Enhanced Cloud2BIM Client - Complete Workflow", style="blue bold")
        
        # Step 1: Process PTX files
        temp_ply = "temp_merged.ply"
        if not self.process_ptx_files(ptx_files, temp_ply):
            return False
        
        try:
            # Step 2: Submit job
            job_id = self.submit_job(temp_ply, config_file)
            if not job_id:
                return False
            
            # Step 3: Monitor progress
            success = False
            if use_sse:
                console.print("📊 Attempting SSE monitoring...", style="blue")
                success = self.monitor_with_sse(job_id)
                
                if not success:
                    console.print("📊 SSE failed, falling back to polling...", style="yellow")
                    success = self.monitor_with_polling(job_id)
            else:
                success = self.monitor_with_polling(job_id)
            
            # Step 4: Download results if successful
            if success:
                self.download_results(job_id)
                
                # Show final summary
                console.print("\n🎉 Conversion Complete!", style="green bold")
                table = Table(title="Job Summary")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="green")
                table.add_row("Job ID", job_id)
                table.add_row("Input Files", ", ".join([Path(f).name for f in ptx_files]))
                table.add_row("Status", "✅ Completed")
                console.print(table)
                
                return True
            else:
                console.print("\n❌ Conversion failed", style="red bold")
                return False
                
        finally:
            # Clean up temporary PLY file
            if os.path.exists(temp_ply):
                os.remove(temp_ply)
                console.print(f"🧹 Cleaned up temporary file: {temp_ply}", style="dim")

def main():
    """Demo of the enhanced client"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Cloud2BIM Client")
    parser.add_argument("ptx_files", nargs="+", help="PTX files to process")
    parser.add_argument("--config", default="app/config/config.yaml", help="Configuration file")
    parser.add_argument("--server", default="http://localhost:8001", help="Server URL")
    parser.add_argument("--no-sse", action="store_true", help="Disable SSE, use polling only")
    
    args = parser.parse_args()
    
    client = EnhancedProgressClient(args.server)
    
    # Validate input files
    for ptx_file in args.ptx_files:
        if not os.path.exists(ptx_file):
            console.print(f"❌ PTX file not found: {ptx_file}", style="red")
            return
    
    if not os.path.exists(args.config):
        console.print(f"❌ Config file not found: {args.config}", style="red")
        return
    
    # Run the complete workflow
    success = client.process_and_convert(
        ptx_files=args.ptx_files,
        config_file=args.config,
        use_sse=not args.no_sse
    )
    
    if success:
        console.print("\n🎯 All done! Check the results directory.", style="green bold")
    else:
        console.print("\n💥 Something went wrong. Check the logs above.", style="red bold")

if __name__ == "__main__":
    main()
