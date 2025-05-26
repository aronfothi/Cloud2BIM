import requests
from requests.exceptions import RequestException
from pathlib import Path
import time
import argparse
import os
import open3d as o3d
import numpy as np
import tempfile
import sys
from typing import List

# Import read_point_cloud function from the app
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))
from core.point_cloud import read_point_cloud

# Default server URL
DEFAULT_SERVER_URL = "http://localhost:8000"  # Keep existing default or update if necessary
SUPPORTED_FORMATS = [".ply", ".ptx", ".xyz", ".pcd"]  # Added PCD as a common format


def read_custom_ptx(file_path: str, downsample_steps=1) -> o3d.geometry.PointCloud:
    """
    Read a PTX file in the format used in our test data.

    The expected PTX format is:
    - Line 1: Number of rows
    - Line 2: Number of columns
    - Line 3: Scanner position (3 values)
    - Line 4-6: Scanner axes (3 values each)
    - Line 7-10: Transformation matrix (4 values each)
    - Line 11: Additional info
    - Remaining lines: Point data (x, y, z, intensity, r, g, b)

    Args:
        file_path: Path to the PTX file

    Returns:
        Open3D PointCloud object
    """
    points = []
    colors = []

    try:
        with open(file_path, "r") as f:
            lines = [line.strip() for line in f.readlines()]

            # Parse header
            if len(lines) < 11:
                raise ValueError("PTX file too short")

            # Read rows and columns (for validation, but not used in processing)
            _ = int(lines[0])  # rows
            _ = int(lines[1])  # cols

            # Skip the scanner position and axes info (lines 3-6)
            # Skip the transformation matrix (lines 7-10)

            # Start reading point data from line 11
            data_start = 11

            for i in range(data_start, len(lines), downsample_steps):
                line = lines[i]
                if not line:
                    continue

                try:
                    values = [float(x) for x in line.split()]
                    if len(values) >= 3:  # At least XYZ coordinates
                        points.append(values[:3])
                        if len(values) >= 7:  # Has RGB values
                            # Normalize RGB values to [0,1] range if they're in [0,255]
                            r, g, b = values[4:7]
                            if max(r, g, b) > 1.0:
                                r, g, b = r / 255.0, g / 255.0, b / 255.0
                            colors.append([r, g, b])
                except (ValueError, IndexError):
                    # Skip invalid lines
                    continue
    except Exception as e:
        raise ValueError(f"Failed to read PTX file {file_path}: {str(e)}")

    if not points:
        raise ValueError(f"No valid points found in PTX file: {file_path}")

    # Create Open3D point cloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np.array(points))

    if colors and len(colors) == len(points):
        pcd.colors = o3d.utility.Vector3dVector(np.array(colors))

    return pcd


def merge_point_clouds(
    pcd_files: List[str | Path], subsample: int = 1
) -> o3d.geometry.PointCloud | None:
    """
    Merges multiple point cloud files into a single point cloud.

    Args:
        pcd_files: List of paths to point cloud files
        subsample: Read every nth point for PTX files (default=1, read all points)

    Returns:
        Merged point cloud as an Open3D PointCloud object, or None if merging fails
    """
    if not pcd_files:
        return None

    merged_pcd = o3d.geometry.PointCloud()
    points_list = []
    colors_list = []

    for file_path in pcd_files:
        pcd = read_point_cloud(str(file_path), subsample=subsample)
        if pcd is None:
            print(f"Warning: Failed to read {file_path}, skipping...")
            continue

        points_list.append(np.asarray(pcd.points))
        if pcd.has_colors():
            colors_list.append(np.asarray(pcd.colors))

    if not points_list:
        return None

    # Combine all points
    merged_points = np.vstack(points_list)
    merged_pcd.points = o3d.utility.Vector3dVector(merged_points)

    # Combine colors if all point clouds had colors
    if len(colors_list) == len(points_list) and all(c is not None for c in colors_list):
        merged_colors = np.vstack(colors_list)
        merged_pcd.colors = o3d.utility.Vector3dVector(merged_colors)

    return merged_pcd


def upload_files(
    server_url: str, merged_pcd_path: str | Path, config_path: str | Path
) -> str | None:
    """
    Uploads the merged PLY point cloud and YAML config file to the server.

    Args:
        server_url: URL of the Cloud2BIM server
        merged_pcd_path: Path to the merged point cloud file (PLY format)
        config_path: Path to the YAML configuration file

    Returns:
        Job ID if successful, None otherwise
    """
    upload_url = f"{server_url}/convert"

    # Convert paths to strings and check existence
    pcd_path_str = str(merged_pcd_path)
    config_path_str = str(config_path)

    if not os.path.exists(pcd_path_str):
        print(f"Error: Merged point cloud file not found at {pcd_path_str}")
        return None
    if not os.path.exists(config_path_str):
        print(f"Error: Configuration file not found at {config_path_str}")
        return None

    try:
        # The server expects point_cloud_data and config_file parameters
        with open(merged_pcd_path, "rb") as pcd_file, open(config_path, "rb") as config_file_obj:
            files = {
                "point_cloud_file": (
                    os.path.basename(merged_pcd_path),
                    pcd_file,
                    "application/octet-stream",
                ),  # Sending as PLY
                "config_file": (
                    os.path.basename(config_path),
                    config_file_obj,
                    "application/x-yaml",
                ),
            }
            print(f"Uploading {merged_pcd_path} and {config_path} to {upload_url}...")
            response = requests.post(
                upload_url, files=files, timeout=60
            )  # Increased timeout for potentially larger merged file
            response.raise_for_status()

            job_data = response.json()
            job_id = job_data.get("job_id")
            print(f"Successfully started job. Job ID: {job_id}")
            return job_id
    except requests.exceptions.RequestException as e:
        print(f"Error uploading files: {e}")
        if hasattr(e, "response") and e.response is not None:
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
            response = requests.get(
                status_url, timeout=40
            )  # Increased timeout from 20 to 30 seconds
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
        except RequestException as e:
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
        response = requests.get(
            download_url, stream=True, timeout=60
        )  # Added timeout, stream for large files
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Successfully downloaded {filename} to {output_path}")
        return True
    except RequestException as e:
        print(f"Error downloading {filename}: {e}")
        if hasattr(e, "response") and e.response is not None:
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
    parser.add_argument(
        "point_cloud_files",
        nargs="+",
        help=f"Path(s) to point cloud file(s). Supported formats: {SUPPORTED_FORMATS}",
    )
    parser.add_argument("config_file", help="Path to the .yaml configuration file.")
    parser.add_argument(
        "--server_url",
        default=DEFAULT_SERVER_URL,
        help=f"URL of the Cloud2BIM server (default: {DEFAULT_SERVER_URL}).",
    )
    parser.add_argument(
        "--output_dir",
        default="./out",
        help="Directory to save downloaded result files (default: ./out directory).",
    )
    parser.add_argument(
        "--merged_output_filename",
        default="merged_point_cloud.ply",
        help="Filename for the temporary merged PLY file (default: merged_point_cloud.ply).",
    )
    parser.add_argument(
        "--subsample",
        type=int,
        default=1,
        help="Read every nth point for PTX files to reduce file size (default: 1, read all points)",
    )

    args = parser.parse_args()

    print(f"Using Cloud2BIM server at: {args.server_url}")
    if args.subsample > 1:
        print(f"Subsampling point clouds: reading every {args.subsample}th point")

    # Validate point cloud files
    valid_pcd_files = []
    for f_path in args.point_cloud_files:
        if not os.path.exists(f_path):
            print(f"Error: Point cloud file not found at {f_path}")
            continue
        if not any(f_path.lower().endswith(ext) for ext in SUPPORTED_FORMATS):
            print(
                f"Error: Unsupported file format for {f_path}. Supported are: {SUPPORTED_FORMATS}"
            )
            continue
        valid_pcd_files.append(f_path)

    if not valid_pcd_files:
        print("No valid point cloud files provided. Exiting.")
        return

    if not os.path.exists(args.config_file):
        print(f"Error: Configuration file not found at {args.config_file}")
        return

    # 1. Merge point clouds if multiple are provided, or prepare single file
    # Call read_point_cloud with subsample parameter
    merged_pcd = None
    if len(valid_pcd_files) > 1:
        print(f"Merging {len(valid_pcd_files)} point cloud files...")
        # Update merge_point_clouds call to use subsampling
        merged_pcd = merge_point_clouds(valid_pcd_files, subsample=args.subsample)
        if not merged_pcd:
            print("Failed to merge point clouds. Exiting.")
            return
    elif len(valid_pcd_files) == 1:
        print(f"Processing single point cloud file: {valid_pcd_files[0]}")
        merged_pcd = read_custom_ptx(valid_pcd_files[0], downsample_steps=args.subsample)
        if not merged_pcd:
            print(f"Failed to read point cloud file {valid_pcd_files[0]}. Exiting.")
            return

    # Save merged/single PCD to a temporary PLY file for upload
    # Using a temporary file to ensure it's cleaned up
    with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as tmp_ply_file:
        temp_ply_path = tmp_ply_file.name

    try:
        if not o3d.io.write_point_cloud(
            temp_ply_path, merged_pcd, write_ascii=False
        ):  # Binary PLY is more compact
            print(f"Error: Failed to write merged point cloud to {temp_ply_path}")
            return
        print(f"Merged point cloud saved temporarily to {temp_ply_path}")

        # 2. Upload files and get job ID
        # The upload_files function now takes the path to the (potentially merged) PLY file
        job_id = upload_files(args.server_url, temp_ply_path, args.config_file)
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_ply_path):
            os.remove(temp_ply_path)
            print(f"Cleaned up temporary file {temp_ply_path}")

    if not job_id:
        print("Failed to start conversion job. Exiting.")
        return

    # 3. Poll for job status
    status_data = poll_job_status(args.server_url, job_id)
    if not status_data:
        print("Failed to get final job status. Exiting.")
        return

    # 4. If completed, download results
    if status_data.get("status") == "completed":
        print("Job completed successfully. Downloading results...")

        # Create output directory if it doesn't exist
        os.makedirs(args.output_dir, exist_ok=True)

        ifc_downloaded = download_result_file(args.server_url, job_id, "model.ifc", args.output_dir)
        # Assuming point_mapping.json is still a relevant output
        mapping_downloaded = download_result_file(
            args.server_url, job_id, "point_mapping.json", args.output_dir
        )

        if ifc_downloaded:
            print(f"IFC model saved as {job_id}_model.ifc in {os.path.abspath(args.output_dir)}")
        if mapping_downloaded:
            print(
                f"Point mapping saved as {job_id}_point_mapping.json in {os.path.abspath(args.output_dir)}"
            )
    elif status_data.get("status") == "failed":
        error_message = status_data.get(
            "error", status_data.get("message", "No specific error message.")
        )
        print(f"Job failed: {error_message}")
    else:
        print("Job did not complete successfully. No results to download.")


if __name__ == "__main__":
    main()
