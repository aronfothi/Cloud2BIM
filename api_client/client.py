import requests
import time
import json
import os
from typing import Optional, Dict, Any, Callable
import sseclient
import open3d as o3d  # Added for point cloud conversion
import numpy as np    # Added for point cloud conversion
import tempfile       # Added for temporary file management

class Cloud2BIMAPIClientError(Exception):
    """Custom exception for Cloud2BIM API Client errors"""
    pass

class Cloud2BIMAPIClient:
    """API Client for interacting with the Cloud2BIM service."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 60):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

    def _convert_ptx_to_ply(self, ptx_path: str) -> str:
        """Converts a PTX file to a temporary PLY file.

        Args:
            ptx_path: Path to the PTX file.

        Returns:
            Path to the temporary PLY file.

        Raises:
            Cloud2BIMAPIClientError: If conversion fails.
        """
        print(f"Converting PTX file {ptx_path} to PLY...")
        try:
            # Read PTX file (simplified parser, assumes format: line count, then X Y Z R G B I lines)
            # This is a basic parser. For robust PTX parsing, a more comprehensive library or logic is needed.
            # For now, we assume a simple structure or that Cloud2BIM_web's ptx_utils can be adapted/used.
            # Let's simulate a basic PTX read and Open3D conversion.
            # A more robust PTX reader would be needed for production.
            
            points = []
            colors = [] # Optional

            with open(ptx_path, 'r') as f:
                # Skip header lines if any - PTX structure can vary.
                # For scan6.ptx, it seems to be:
                # num_cols
                # num_rows
                # 3x4 transformation matrix (scanner pose)
                # 3x3 transformation matrix (scanner pose)
                # 4x4 transformation matrix (scanner pose)
                # Then points X Y Z Intensity R G B (where R G B might be 0 if not present)
                
                # Skipping header for a common PTX structure (10 lines of header)
                # This is a guess and might need adjustment for specific PTX files.
                header_lines_to_skip = 0
                try:
                    # Attempt to read dimensions first
                    num_cols = int(f.readline().strip())
                    num_rows = int(f.readline().strip())
                    header_lines_to_skip = 8 # Remaining transform lines
                    for _ in range(header_lines_to_skip):
                        f.readline()
                    
                    print(f"PTX dimensions: {num_cols}x{num_rows}. Total points: {num_cols * num_rows}")

                except ValueError:
                    print("Could not parse PTX header for dimensions, attempting direct point read.")
                    f.seek(0) # Reset to start if header parsing fails

                point_count = 0
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3: # Must have at least X, Y, Z
                        try:
                            x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                            points.append([x, y, z])
                            
                            # Try to get colors if available (assuming R, G, B are last or after intensity)
                            if len(parts) >= 7: # X Y Z I R G B
                                r, g, b = int(parts[4]), int(parts[5]), int(parts[6])
                                colors.append([r / 255.0, g / 255.0, b / 255.0]) # Normalize to 0-1
                            elif len(parts) == 6: # X Y Z R G B (no intensity)
                                r, g, b = int(parts[3]), int(parts[4]), int(parts[5])
                                colors.append([r / 255.0, g / 255.0, b / 255.0])
                            point_count +=1
                        except ValueError:
                            # Skip lines that cannot be parsed as points
                            continue 
                print(f"Successfully read {point_count} points from PTX.")

            if not points:
                raise Cloud2BIMAPIClientError("No points found in PTX file or failed to parse.")

            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(np.array(points))
            if colors and len(colors) == len(points):
                pcd.colors = o3d.utility.Vector3dVector(np.array(colors))
            
            # Create a temporary PLY file
            temp_ply_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ply")
            ply_path = temp_ply_file.name
            temp_ply_file.close() # Close it so Open3D can write to it

            o3d.io.write_point_cloud(ply_path, pcd, write_ascii=True) # ASCII PLY for better compatibility
            print(f"Successfully converted PTX to temporary PLY: {ply_path}")
            return ply_path

        except Exception as e:
            raise Cloud2BIMAPIClientError(f"Failed to convert PTX to PLY: {e}")

    def submit_job(self, point_cloud_path: str, config_path: str) -> str:
        """Submits a point cloud conversion job to the server.
        Converts PTX to PLY if necessary before submitting.
        Args:
            point_cloud_path: Path to the point cloud file (e.g., .ptx, .xyz, .ply).
            config_path: Path to the YAML configuration file.

        Returns:
            The job ID string if submission is successful.

        Raises:
            Cloud2BIMAPIClientError: If file not found or API request fails.
        """
        if not os.path.exists(point_cloud_path):
            raise Cloud2BIMAPIClientError(f"Point cloud file not found: {point_cloud_path}")
        if not os.path.exists(config_path):
            raise Cloud2BIMAPIClientError(f"Configuration file not found: {config_path}")

        temp_ply_path = None
        original_filename = os.path.basename(point_cloud_path)
        file_to_submit = point_cloud_path

        if point_cloud_path.lower().endswith('.ptx'):
            try:
                temp_ply_path = self._convert_ptx_to_ply(point_cloud_path)
                file_to_submit = temp_ply_path
                original_filename = os.path.basename(point_cloud_path).replace('.ptx', '.ply').replace('.PTX', '.PLY')
                print(f"Submitting converted PLY file: {file_to_submit} (original: {point_cloud_path})")
            except Cloud2BIMAPIClientError as e:
                # If conversion fails, re-raise the error
                if temp_ply_path and os.path.exists(temp_ply_path):
                    os.remove(temp_ply_path)
                raise e


        try:
            with open(file_to_submit, 'rb') as pc_file, \
                 open(config_path, 'rb') as cfg_file:
                files = {
                    'point_cloud_file': (original_filename, pc_file), # Use original or modified PLY filename
                    'config_file': (os.path.basename(config_path), cfg_file)
                }
                
                print(f"Submitting job with point cloud: {file_to_submit} and config: {config_path}")
                response = self.session.post(
                    f"{self.base_url}/convert",
                    files=files,
                    timeout=self.timeout
                )
                response.raise_for_status() 
                
                job_data = response.json()
                print(f"Job submitted successfully. Job ID: {job_data['job_id']}")
                return job_data['job_id']

        except FileNotFoundError as e:
            raise Cloud2BIMAPIClientError(f"File not found during submission: {e}")
        except requests.exceptions.RequestException as e:
            raise Cloud2BIMAPIClientError(f"API request failed during job submission: {e}")
        except KeyError:
            raise Cloud2BIMAPIClientError(f"Failed to parse job_id from response: {response.text}")
        finally:
            # Clean up temporary PLY file if it was created
            if temp_ply_path and os.path.exists(temp_ply_path):
                try:
                    os.remove(temp_ply_path)
                    print(f"Cleaned up temporary PLY file: {temp_ply_path}")
                except OSError as e:
                    print(f"Warning: Failed to clean up temporary PLY file {temp_ply_path}: {e}")

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Retrieves the current status of a job.

        Args:
            job_id: The ID of the job to check.

        Returns:
            A dictionary containing the job status information.

        Raises:
            Cloud2BIMAPIClientError: If the API request fails.
        """
        try:
            response = self.session.get(
                f"{self.base_url}/status/{job_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Cloud2BIMAPIClientError(f"Failed to get job status for {job_id}: {e}")

    def stream_progress(self, job_id: str, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """Streams progress updates for a job using Server-Sent Events (SSE).

        Args:
            job_id: The ID of the job to stream progress for.
            progress_callback: An optional function to call with each progress update.
                               The callback will receive a dictionary containing the progress data.
        Raises:
            Cloud2BIMAPIClientError: If the SSE connection fails or an error occurs during streaming.
        """
        sse_url = f"{self.base_url}/api/stream/progress/{job_id}" # Corrected SSE URL
        print(f"Connecting to SSE stream for job {job_id} at {sse_url}")
        client = None # Ensure client is defined for finally block
        try:
            response = self.session.get(sse_url, stream=True, headers={'Accept': 'text/event-stream'})
            response.raise_for_status()
            client = sseclient.SSEClient(response)

            for event in client.events():
                if event.event == 'progress':
                    try:
                        progress_data = json.loads(event.data)
                        if progress_callback:
                            progress_callback(progress_data)
                        else:
                            print(f"Progress update: {progress_data}")
                        
                    except json.JSONDecodeError:
                        print(f"Received non-JSON SSE data for progress event: {event.data}")
                    except Exception as e:
                        print(f"Error processing SSE progress event: {e}")
                elif event.event == 'complete':
                    try:
                        completion_data = json.loads(event.data)
                        print(f"Job {job_id} finished with status: {completion_data.get('final_status')}")
                        if progress_callback: 
                            progress_callback(completion_data) 
                        break 
                    except json.JSONDecodeError:
                        print(f"Received non-JSON SSE data for complete event: {event.data}")
                    except Exception as e:
                        print(f"Error processing SSE complete event: {e}")
                elif event.event == 'error':
                    try:
                        error_data = json.loads(event.data)
                        error_message = error_data.get("error", "Unknown SSE error")
                    except json.JSONDecodeError:
                        error_message = event.data # Use raw data if not JSON
                    print(f"SSE stream error for job {job_id}: {error_message}")
                    # Raise an exception to stop streaming on server-sent errors
                    raise Cloud2BIMAPIClientError(f"SSE stream error: {error_message}")
                elif event.data: 
                    try:
                        # Attempt to parse as JSON, but handle non-JSON gracefully
                        if event.data.startswith('{') and event.data.endswith('}'):
                            generic_data = json.loads(event.data)
                            print(f"Generic SSE message: {generic_data}")
                            if progress_callback:
                                progress_callback(generic_data)
                            # Check for completion status in generic messages too
                            if generic_data.get('status') in ['completed', 'failed']:
                                print(f"Job {job_id} finished based on generic message: {generic_data.get('status')}")
                                break
                        elif event.data != "ping": # Ignore pings
                           print(f"Received non-JSON generic SSE data: {event.data}")
                    except json.JSONDecodeError:
                        if event.data != "ping": # Ignore pings
                           print(f"Received non-JSON generic SSE data (decode failed): {event.data}")
                    except Exception as e:
                        print(f"Error processing generic SSE event: {e}")

        except requests.exceptions.RequestException as e:
            raise Cloud2BIMAPIClientError(f"Failed to connect to SSE stream for job {job_id}: {e}")
        except Cloud2BIMAPIClientError: # Re-raise client errors from SSE event handling
            raise
        except Exception as e:
            raise Cloud2BIMAPIClientError(f"An unexpected error occurred during SSE streaming for job {job_id}: {e}")
        finally:
            if client:
                client.close()
            print(f"SSE stream for job {job_id} closed.")

    def download_results(self, job_id: str, output_dir: str) -> None:
        """Downloads the IFC model and point mapping JSON for a completed job.

        Args:
            job_id: The ID of the completed job.
            output_dir: The directory to save the downloaded files.

        Raises:
            Cloud2BIMAPIClientError: If the API request fails or files cannot be saved.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        results_to_download = {
            "model.ifc": f"{self.base_url}/results/{job_id}/model.ifc",
            "point_mapping.json": f"{self.base_url}/results/{job_id}/point_mapping.json"
        }

        for filename, url in results_to_download.items():
            try:
                print(f"Downloading {filename} for job {job_id} from {url}...")
                response = self.session.get(url, timeout=self.timeout, stream=True)
                response.raise_for_status()
                
                output_path = os.path.join(output_dir, filename)
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Successfully downloaded {filename} to {output_path}")
            except requests.exceptions.RequestException as e:
                raise Cloud2BIMAPIClientError(f"Failed to download {filename} for job {job_id}: {e}")
            except IOError as e:
                raise Cloud2BIMAPIClientError(f"Failed to save {filename} to {output_path}: {e}")

def default_progress_printer(progress_data: Dict[str, Any]):
    """A default callback function to print progress updates in a structured way."""
    status = progress_data.get('status', 'N/A')
    stage = progress_data.get('progress', {}).get('stage', 'N/A')
    stage_desc = progress_data.get('progress', {}).get('stage_description', 'N/A')
    percentage = progress_data.get('progress', {}).get('percentage', 0)
    
    print(f"[Job Progress] Status: {status} | Stage: {stage} ({stage_desc}) | Percentage: {percentage}%")
    if 'performance' in progress_data and progress_data['performance']:
        perf = progress_data['performance']
        cpu = perf.get('cpu_usage_percent', 'N/A')
        mem = perf.get('memory_usage_mb', 'N/A')
        print(f"  Performance: CPU {cpu}% | Memory {mem} MB")

if __name__ == "__main__":
    # Configuration
    API_BASE_URL = "http://localhost:8001"
    POINT_CLOUD_FILE = "/home/fothar/Cloud2BIM_web/test_data/scan6.ptx" 
    # Create a dummy config file if it doesn't exist for testing
    CONFIG_FILE_PATH = "/home/fothar/Cloud2BIM_web/api_client/dummy_config.yaml"
    OUTPUT_DIR = "/home/fothar/Cloud2BIM_web/api_client/output_results"

    if not os.path.exists(CONFIG_FILE_PATH):
        print(f"Creating dummy configuration file at {CONFIG_FILE_PATH}")
        with open(CONFIG_FILE_PATH, 'w') as f:
            f.write("ifc:\n  project_name: \"API Client Test Project\"\n")
            f.write("pc_resolution: 0.05\n") # Add some basic config
            f.write("preprocessing:\n  voxel_size: 0.1\n")

    if not os.path.exists(POINT_CLOUD_FILE):
        print(f"ERROR: Point cloud file {POINT_CLOUD_FILE} not found. Please ensure the path is correct.")
        exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    client = Cloud2BIMAPIClient(base_url=API_BASE_URL)

    try:
        # 1. Submit the job
        job_id = client.submit_job(POINT_CLOUD_FILE, CONFIG_FILE_PATH)

        if job_id:
            # 2. Stream progress information
            print(f"\n--- Streaming progress for Job ID: {job_id} ---")
            client.stream_progress(job_id, progress_callback=default_progress_printer)
            print("--- Progress streaming finished ---\n")

            # 3. Verify final status (optional, as SSE should indicate completion)
            final_status = client.get_job_status(job_id)
            print(f"Final job status: {final_status.get('status')}")
            print(json.dumps(final_status, indent=2))

            # 4. Download results if completed
            if final_status.get('status') == 'completed':
                print(f"\n--- Downloading results for Job ID: {job_id} ---")
                client.download_results(job_id, OUTPUT_DIR)
                print(f"Results for job {job_id} downloaded to {OUTPUT_DIR}")
            else:
                print(f"Job {job_id} did not complete successfully. Status: {final_status.get('status')}. Skipping download.")

    except Cloud2BIMAPIClientError as e:
        print(f"API Client Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
