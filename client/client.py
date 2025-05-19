import requests
import time
import argparse
import os

# Default server URL
DEFAULT_SERVER_URL = "http://localhost:8000"

def upload_files(server_url: str, ptx_path: str, config_path: str) -> str | None:
    """Uploads PTX and YAML config files to the server and returns the job ID."""
    upload_url = f"{server_url}/convert"
    
    if not os.path.exists(ptx_path):
        print(f"Error: Point cloud file not found at {ptx_path}")
        return None
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at {config_path}")
        return None

    try:
        with open(ptx_path, 'rb') as ptx_file, open(config_path, 'rb') as config_file:
            files = {
                'ptx_file': (os.path.basename(ptx_path), ptx_file, 'application/octet-stream'),
                'config_file': (os.path.basename(config_path), config_file, 'application/x-yaml')
            }
            print(f"Uploading {ptx_path} and {config_path} to {upload_url}...")
            response = requests.post(upload_url, files=files, timeout=30) # Added timeout
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            
            job_data = response.json()
            job_id = job_data.get("job_id")
            print(f"Successfully started job. Job ID: {job_id}")
            return job_id
    except requests.exceptions.RequestException as e:
        print(f"Error uploading files: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"Server response: {e.response.json()}")
            except ValueError:
                print(f"Server response: {e.response.text}")
        return None
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return None

def poll_job_status(server_url: str, job_id: str) -> dict | None:
    """Polls the job status until it's completed or failed."""
    status_url = f"{server_url}/status/{job_id}"
    print(f"Polling job status for {job_id} at {status_url}...")
    
    while True:
        try:
            response = requests.get(status_url, timeout=10) # Added timeout
            response.raise_for_status()
            status_data = response.json()
            
            status = status_data.get("status")
            stage = status_data.get("stage", "N/A")
            progress = status_data.get("progress", 0)
            message = status_data.get("message", "")

            print(f"Status: {status}, Stage: {stage}, Progress: {progress}%, Message: {message}")

            if status in ["completed", "failed"]:
                return status_data
            
            time.sleep(5)  # Poll every 5 seconds
        except requests.exceptions.RequestException as e:
            print(f"Error polling status: {e}")
            return None
        except KeyboardInterrupt:
            print("Polling interrupted by user.")
            return None

def download_result_file(server_url: str, job_id: str, filename: str, output_dir: str) -> bool:
    """Downloads a result file (IFC or JSON mapping) for a completed job."""
    download_url = f"{server_url}/results/{job_id}/{filename}"
    output_path = os.path.join(output_dir, f"{job_id}_{filename}")
    os.makedirs(output_dir, exist_ok=True)

    print(f"Downloading {filename} from {download_url} to {output_path}...")
    try:
        response = requests.get(download_url, stream=True, timeout=60) # Added timeout, stream for large files
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Successfully downloaded {filename} to {output_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {filename}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"Server response: {e.response.json()}")
            except ValueError:
                print(f"Server response: {e.response.text}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while downloading {filename}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="CLI client for the Cloud2BIM service.")
    parser.add_argument("ptx_file", help="Path to the .ptx or .xyz point cloud file.")
    parser.add_argument("config_file", help="Path to the .yaml configuration file.")
    parser.add_argument("--server_url", default=DEFAULT_SERVER_URL, help=f"URL of the Cloud2BIM server (default: {DEFAULT_SERVER_URL}).")
    parser.add_argument("--output_dir", default=".", help="Directory to save downloaded result files (default: current directory).")

    args = parser.parse_args()

    print(f"Using Cloud2BIM server at: {args.server_url}")

    # 1. Upload files and get job ID
    job_id = upload_files(args.server_url, args.ptx_file, args.config_file)
    if not job_id:
        print("Failed to start conversion job. Exiting.")
        return

    # 2. Poll for job status
    status_data = poll_job_status(args.server_url, job_id)
    if not status_data:
        print("Failed to get final job status. Exiting.")
        return

    # 3. If completed, download results
    if status_data.get("status") == "completed":
        print("Job completed successfully. Downloading results...")
        ifc_downloaded = download_result_file(args.server_url, job_id, "model.ifc", args.output_dir)
        mapping_downloaded = download_result_file(args.server_url, job_id, "point_mapping.json", args.output_dir)
        
        if ifc_downloaded:
            print(f"IFC model saved as {job_id}_model.ifc in {os.path.abspath(args.output_dir)}")
        if mapping_downloaded:
            print(f"Point mapping saved as {job_id}_point_mapping.json in {os.path.abspath(args.output_dir)}")
    elif status_data.get("status") == "failed":
        print(f"Job failed: {status_data.get('message', 'No specific error message.')}")
    else:
        print("Job did not complete successfully. No results to download.")

if __name__ == "__main__":
    main()
