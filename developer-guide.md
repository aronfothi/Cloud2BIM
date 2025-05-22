# Developer Guide: Cloud2BIM Async Web Service

This guide provides instructions for setting up the development environment, running the service, and understanding the project structure.

## 1. Project Overview

The Cloud2BIM Async Web Service is a FastAPI application designed to convert 3D point cloud files (PTX/XYZ) and a YAML configuration into IFC BIM models. It uses the Cloud2BIM algorithm for point cloud segmentation and IfcOpenShell for IFC file generation. The processing is handled asynchronously to manage potentially long-running conversion tasks.

## 2. Prerequisites

*   **Python 3.10+**: Ensure you have a compatible Python version installed.
*   **Git**: For version control.
*   **Virtual Environment Tool**: `venv` (recommended) or `conda`.

## 3. Setup Instructions

### 3.1. Clone the Repository

```bash
git clone <your-repository-url> # Replace with your actual repository URL
cd Cloud2BIM_web
```

### 3.2. Create and Activate Virtual Environment

Using `venv`:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3.3. Install Dependencies

All required Python packages are listed in `requirements.txt`.
```bash
pip install -r requirements.txt
```
This will install FastAPI, Uvicorn, IfcOpenShell, NumPy, Open3D, PyYAML, requests, and other necessary libraries.

### 3.4. Configuration

The main application configuration is handled via YAML files.
*   Global application settings (if any) might be in `app/config/settings.py` or similar.
*   Job-specific configurations are uploaded by the user with each conversion request (e.g., `sample_config.yaml`). These define parameters for the Cloud2BIM processing pipeline.

Default processing parameters can be found in `app/config/config.yaml`. This file is used as a fallback or template if a user doesn't provide a complete configuration.

## 4. Running the Service Locally

### 4.1. Start the FastAPI Server

Use Uvicorn to run the FastAPI application:
```bash
uvicorn app.main:app --reload --port 8005
```
*   `--reload`: Enables auto-reloading when code changes, useful for development.
*   `--port 8005`: Specifies the port number.

Once running, the API documentation (Swagger UI) will be available at [http://localhost:8005/docs](http://localhost:8005/docs).

### 4.2. Using the CLI Client

A command-line client is provided in `client/client.py` to interact with the service.
The client is responsible for reading various point cloud file formats (e.g., PLY, PTX, XYZ), merging them if multiple files are provided, and sending a single standardized point cloud file to the server.
```bash
python client/client.py <path_to_point_cloud_file_or_files> <path_to_config_yaml> --server_url http://localhost:8005 --output_dir ./job_outputs
```
Example:
```bash
python client/client.py tests/data/scan6.ptx tests/data/sample_config.yaml --server_url http://localhost:8005 --output_dir ./downloaded_results
```
This will upload the files, poll for status, and download the resulting IFC model and point mapping JSON.

## 5. Project Structure

```
Cloud2BIM_web/
├── .github/
│   └── copilot-instructions.md  # Instructions for GitHub Copilot
├── .venv/                         # Python virtual environment
├── app/                           # Main application code
│   ├── __init__.py
│   ├── api/                       # FastAPI endpoints and request/response models
│   │   ├── __init__.py
│   │   ├── endpoints.py           # API route definitions
│   │   └── schemas.py             # Pydantic models for API
│   ├── core/                      # Core processing logic
│   │   ├── __init__.py
│   │   ├── aux_functions.py       # Helper functions (config loading, etc.)
│   │   ├── cloud2entities.py      # Point cloud segmentation logic
│   │   ├── generate_ifc.py        # IFC model generation
│   │   ├── job_processor.py       # Background job processing
│   │   ├── plotting_functions.py  # Plotting utilities (if any)
│   │   └── storage.py             # File storage utilities
│   ├── config/                    # Configuration files
│   │   ├── __init__.py
│   │   └── config.yaml            # Default processing parameters
│   ├── models/                    # Data models (e.g. for job status)
│   │   ├── __init__.py
│   │   └── job_model.py
│   └── main.py                    # FastAPI application entry point
├── client/                        # CLI client
│   └── client.py
├── data/                          # (Optional) Default data, e.g. sample point clouds
├── docs/                          # Documentation
│   └── implementation_notes.md
├── jobs/                          # Directory where job data is stored (dynamically created)
│   └── <job_id>/
│       ├── input/
│       ├── output/
│       └── job_status.json
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── api/
│   │   └── test_endpoints.py
│   ├── core/
│   │   └── test_processing.py
│   └── data/                      # Sample data for tests
│       ├── sample_config.yaml
│       └── scan6.ptx
├── .gitignore
├── developer-guide.md             # This file
├── LICENSE
├── README.md
├── requirements.txt
├── todo.md
└── ... (other original Cloud2BIM utility scripts if retained at top level)
```

### Key Modules:

*   **`app/main.py`**: Initializes the FastAPI app.
*   **`app/api/endpoints.py`**: Defines the HTTP endpoints (`/convert`, `/status/{job_id}`, `/results/{job_id}/...`).
*   **`app/api/schemas.py`**: Contains Pydantic models for request and response data validation.
*   **`app/core/job_processor.py`**: Manages the lifecycle of a conversion job, including calling the Cloud2BIM processing steps. This is where the asynchronous processing logic resides.
*   **`app/core/cloud2entities.py`**: Contains the `CloudToBimProcessor` class, which encapsulates the core point cloud segmentation algorithms (slab detection, wall detection, etc.) and orchestrates the conversion process based on the job-specific configuration. This module is adapted from the original Cloud2BIM project.
*   **`app/core/generate_ifc.py`**: Handles the creation of the IFC file using IfcOpenShell based on the segmented entities.
*   **`app/core/storage.py`**: Provides functions for saving uploaded files and managing job-specific data persistence in the `jobs/` directory.
*   **`app/core/aux_functions.py`**: Contains utility functions, notably `load_config_and_variables` for parsing YAML configuration files.
*   **`app/models/job_model.py`**: Defines the Pydantic model for `JobStatus`, used for tracking and reporting job progress.
*   **`client/client.py`**: A Python script that acts as a client to the web service. It handles reading various point cloud formats, merging multiple files if necessary, and interacting with the server API.

## 6. Development Workflow

1.  **Create a new branch** for your feature or bugfix:
    ```bash
    git checkout -b feature/my-new-feature
    ```
2.  **Make your code changes.**
    *   Follow PEP 8 guidelines.
    *   Add type hints and docstrings.
    *   Use the `logging` module for output, not `print()`.
    *   Ensure heavy computations are asynchronous or run in a thread pool.
3.  **Write or update tests** in the `tests/` directory.
4.  **Run tests** (details TBD, likely using `pytest`).
    ```bash
    # pytest (once test runner is configured)
    ```
5.  **Lint and format your code:**
    ```bash
    black .
    flake8 .
    ```
6.  **Commit your changes** with a clear commit message.
    ```bash
    git add .
    git commit -m "feat: Implement my new feature"
    ```
7.  **Push to the repository and open a Pull Request.**

## 7. Key Technologies and Libraries

*   **FastAPI**: Modern, fast web framework for building APIs.
*   **Pydantic**: Data validation and settings management using Python type annotations.
*   **IfcOpenShell**: Library for working with IFC files.
*   **Open3D, NumPy, OpenCV**: For point cloud and numerical processing (dependencies of Cloud2BIM).
*   **PyYAML**: For parsing YAML configuration files.
*   **Uvicorn**: ASGI server for running FastAPI.
*   **HTTPX** (or **Requests** for the client): For making HTTP requests.

## 8. Asynchronous Processing

The core conversion process is CPU-bound and can take time. To avoid blocking the server, FastAPI's `BackgroundTasks` or `asyncio.to_thread` (or a similar mechanism like `fastapi.concurrency.run_in_threadpool`) is used in `app/api/endpoints.py` to offload the `process_job` function in `app/core/job_processor.py`.

The `jobs` dictionary in `app/main.py` (or a more robust job store) keeps track of the status of each job.

## 9. Configuration Management

*   Job-specific configurations are uploaded as YAML files with each `/convert` request.
*   The `app/core/aux_functions.py::load_config_and_variables` function is responsible for loading these YAML files. It's designed to be called per-job, ensuring that each job uses its specific configuration.
*   The `config_params` dictionary returned by this function is then used by the `CloudToBimProcessor` in `app/core/cloud2entities.py` to guide the processing pipeline (to `detect_elements`, `IFCmodel`, etc.).

## 10. Error Handling and Logging

*   FastAPI's exception handling mechanisms are used for API-level errors.
*   The `job_status.json` file for each job includes an `error` field to report issues during background processing.
*   Standard Python `logging` should be configured and used throughout the application for diagnostics.

## 11. Testing

*   Unit and integration tests are located in the `tests/` directory.
*   `pytest` is the recommended test runner.
*   `tests/api/` contains tests for the FastAPI endpoints.
*   `tests/core/` contains tests for the core processing logic.
*   Sample data for testing is in `tests/data/`.

(Further details on running specific tests and test coverage to be added.)

## 12. Future Enhancements / TODOs

Refer to `todo.md` for a list of planned features and improvements. Key areas include:
*   More robust error handling and reporting.
*   Comprehensive test coverage.
*   Authentication and authorization.
*   Job queueing system (e.g., Celery) for scalability.
*   Automatic cleanup of old job data.

---

This guide should help you get started with developing the Cloud2BIM Async Web Service. If you have questions, please refer to the codebase or open an issue.
