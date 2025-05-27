# Cloud2BIM API Client - Developer Documentation

## 1. Overview

This document provides developer documentation for the `Cloud2BIMAPIClient`, a Python client designed to interact with the Cloud2BIM web service. The client facilitates submitting point cloud conversion jobs, monitoring their progress in real-time using Server-Sent Events (SSE), and downloading the resulting IFC models and point mapping data.

This client is located in the `/home/fothar/Cloud2BIM_web/api_client/` directory.

## 2. Project Structure

```
api_client/
├── client.py             # The main API client class and example usage.
├── dummy_config.yaml     # A sample configuration file, created if not present.
├── output_results/       # Directory where downloaded results will be stored.
└── README.md             # This developer documentation file.
```

## 3. `Cloud2BIMAPIClient` Class

### 3.1. Initialization

```python
client = Cloud2BIMAPIClient(base_url: str = "http://localhost:8000", timeout: int = 60)
```

- **`base_url`**: The base URL of the Cloud2BIM service (defaults to `http://localhost:8000`).
- **`timeout`**: Default timeout in seconds for HTTP requests (defaults to 60 seconds).

### 3.2. Methods

#### `submit_job(self, point_cloud_path: str, config_path: str) -> str`

Submits a new point cloud conversion job.

- **Args**:
    - `point_cloud_path`: Absolute or relative path to the point cloud file (PTX, XYZ, PLY).
    - `config_path`: Absolute or relative path to the YAML configuration file.
- **Returns**: The `job_id` (string) if the submission is successful.
- **Raises**: `Cloud2BIMAPIClientError` if files are not found or if the API request fails.

#### `get_job_status(self, job_id: str) -> Dict[str, Any]`

Retrieves the current status of a specified job.

- **Args**:
    - `job_id`: The ID of the job to query.
- **Returns**: A dictionary containing the job's status information.
- **Raises**: `Cloud2BIMAPIClientError` if the API request fails.

#### `stream_progress(self, job_id: str, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None)`

Streams real-time progress updates for a job using Server-Sent Events (SSE).

- **Args**:
    - `job_id`: The ID of the job.
    - `progress_callback` (optional): A function that will be called with each progress update. If not provided, progress data is printed to the console. The callback receives a dictionary parsed from the SSE event data.
- **Raises**: `Cloud2BIMAPIClientError` if the SSE connection fails or an error occurs during streaming.

#### `download_results(self, job_id: str, output_dir: str) -> None`

Downloads the resulting IFC model and point mapping JSON file for a completed job.

- **Args**:
    - `job_id`: The ID of the completed job.
    - `output_dir`: The local directory where the result files will be saved. The directory will be created if it doesn't exist.
- **Raises**: `Cloud2BIMAPIClientError` if the API request fails or if there's an issue saving the files.

### 3.3. `Cloud2BIMAPIClientError` Exception

A custom exception class raised by the client for specific errors encountered during its operation, such as file not found, API request failures, or SSE stream issues.

## 4. Helper Functions

### `default_progress_printer(progress_data: Dict[str, Any])`

A sample callback function provided in `client.py` that can be passed to `stream_progress`. It prints formatted progress information to the console, including status, stage, percentage, and performance metrics if available.

## 5. Example Usage (`if __name__ == "__main__":` block in `client.py`)

The `client.py` script includes a main execution block that demonstrates the typical workflow:

1.  **Configuration**: Sets the API base URL, paths for the input point cloud file (`/home/fothar/Cloud2BIM_web/test_data/scan6.ptx`), a dummy configuration file, and an output directory.
2.  **Dummy Config Creation**: If `dummy_config.yaml` doesn't exist in the `api_client` directory, it's created with minimal content for testing purposes.
3.  **File Check**: Verifies the existence of the `scan6.ptx` file.
4.  **Client Instantiation**: Creates an instance of `Cloud2BIMAPIClient`.
5.  **Job Submission**: Calls `submit_job()` with the point cloud and config file.
6.  **Progress Streaming**: If job submission is successful, calls `stream_progress()` using the `default_progress_printer` to display live updates from the server.
7.  **Final Status Check**: After streaming, calls `get_job_status()` to fetch the final status (this is somewhat redundant if SSE correctly signals completion but serves as a verification step).
8.  **Result Download**: If the job status is 'completed', calls `download_results()` to save the `model.ifc` and `point_mapping.json` to the specified `output_dir`.
9.  **Error Handling**: Includes `try...except` blocks to catch `Cloud2BIMAPIClientError` and other potential exceptions.

## 6. Running the Client

1.  **Ensure the Cloud2BIM Server is Running**: The FastAPI server (usually `main.py` in the project root) must be running and accessible at the `API_BASE_URL` (default `http://localhost:8000`).
2.  **Verify Point Cloud File**: Make sure the `scan6.ptx` file exists at `/home/fothar/Cloud2BIM_web/test_data/scan6.ptx`.
3.  **Install Dependencies**: The client requires the `requests` and `sseclient-py` libraries. Ensure they are installed in your Python environment.
    ```bash
    pip install requests sseclient-py
    ```
4.  **Execute the Client Script**:
    Navigate to the project root directory (`/home/fothar/Cloud2BIM_web/`) in your terminal and run:
    ```bash
    python api_client/client.py
    ```

The client will then proceed to submit the job, print live progress logs from the server, and download the results upon completion.

## 7. Dependencies

-   `requests`: For making HTTP requests to the API.
-   `sseclient-py`: For handling Server-Sent Event streams.

## 8. Customization

-   **`API_BASE_URL`**: Modify this in `client.py` if your server runs on a different address or port.
-   **`POINT_CLOUD_FILE`**, **`CONFIG_FILE_PATH`**: Change these paths to use different input files.
-   **`OUTPUT_DIR`**: Specify a different directory for downloaded results.
-   **`progress_callback`**: Implement your own callback function for `stream_progress` to integrate progress updates into other systems or UIs (e.g., updating a GUI, logging to a database).

## 9. Troubleshooting

-   **`Cloud2BIMAPIClientError: Point cloud file not found`**: Ensure the path to `scan6.ptx` is correct and the file exists.
-   **`Cloud2BIMAPIClientError: API request failed ... Connection refused`**: Make sure the Cloud2BIM server is running and accessible at the specified `API_BASE_URL`.
-   **SSE Stream Issues**: Check network connectivity and ensure the server's SSE endpoint (`/api/progress/{job_id}/stream`) is functioning correctly. Firewalls or proxies might interfere with SSE connections.
-   **Permission Denied (for output_dir or dummy_config.yaml)**: Ensure the script has write permissions for the `api_client` directory and its subdirectories.
