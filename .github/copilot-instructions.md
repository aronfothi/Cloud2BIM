# Copilot Instructions

This project is a **FastAPI-based web service** for converting 3D point cloud files into IFC BIM models using the Cloud2BIM algorithm. The codebase is primarily Python 3.10+.

## Project Context
- The service accepts large **PTX/XYZ point cloud files** and a YAML configuration, then performs segmentation to identify slabs, walls, openings, etc., and produces an **IFC file** as output.
- We integrate **Cloud2BIM** logic (point cloud segmentation and IFC generation) into our code. Assume we have access to functions for detection steps (slabs, walls, zones, openings) and use **IfcOpenShell** for IFC creation.
- The processing is intensive, so it runs asynchronously in a background thread or task. We provide a **progress tracking** mechanism so clients can poll job status.

## Technologies and Libraries
- Use **FastAPI** for the web framework (asynchronous where appropriate).
- Use **Pydantic** for request/response models (e.g., defining data schemas for status responses).
- Use **Python async/await** for concurrency. Long-running tasks may be offloaded to a thread or a Celery worker.
- Use **IfcOpenShell** (Python library) to handle IFC model creation.
- Use **Open3D**, **NumPy**, and **OpenCV (cv2)** as needed for point cloud processing (these are dependencies of Cloud2BIM).
- Use **PyYAML** to parse YAML config files.
- Ensure any external commands or file operations are performed securely (avoid arbitrary code execution).
- Read developer-guide.md for the overall project structure and setup.
- Read `todo.md` for specific tasks and features to implement. Update this file as needed to reflect the current state of the project.
- use firecrawl to crawl the web for relevant information and code snippets that can help with implementation.
- Edit the files directly. Not from commands line or terminal.

## Coding Standards
- Follow **PEP 8** style guidelines for Python code. Use clear, descriptive variable and function names (e.g., `process_point_cloud`, `calculate_wall_planes`).
- Include **type hints** for function signatures and key variables to improve clarity (e.g., `def process_job(job_id: str) -> None:`).
- Write **docstrings** for all public functions explaining their purpose, inputs, and outputs. This helps both humans and Copilot.
- Use logging (`logging` module) for debug and info messages instead of print, to facilitate monitoring in production.
- **Do not block** the event loop in FastAPI endpoints: perform heavy computation in background tasks or worker threads. Copilot should suggest using `async def` for endpoints and possibly `await run_in_threadpool()` for CPU-bound calls.
- When writing asynchronous code, use `asyncio` features appropriately (e.g., `asyncio.to_thread` or background tasks) and avoid race conditions on shared data (consider thread safety when updating `jobs` dict).
- For HTTP endpoints, return standardized responses (use Pydantic models or JSON dictionaries). Copilot should generate responses consistent with our API design (e.g., returning job_id and status).
- Validate inputs: ensure file types and sizes are checked. If Copilot writes file-handling code, it should handle exceptions (like file not found or parse errors) gracefully and return proper HTTP errors.
- **Security**: The instructions to Copilot should prefer safe coding patterns. For example, when saving uploaded files, use a safe file name or a generated name, not directly the user’s provided name (to avoid path traversal). Copilot should avoid eval or exec. 
- Use **context managers** for file operations (e.g., `with open(path, 'rb') as f:`) to ensure files are closed properly.
- When generating code for the CLI client, use the **requests** library to call the API, and handle errors (non-200 responses) robustly.

## Aiming for Quality
- We prefer clearer code over clever one-liners. For instance, Copilot should break down complex list comprehensions into understandable loops if it improves readability.
- Write code in a modular way: e.g., separate the FastAPI app declaration, the background job logic, and the Cloud2BIM integration into different modules.
- Add comments in code to explain non-obvious steps, especially when interfacing with Cloud2BIM’s functions or parsing point cloud data.
- The project should be structured for maintainability: Copilot should help generate code that is easy to refactor and test. Encourage writing small helper functions for repetitive tasks (like saving files, updating progress).
- Where relevant, Copilot may suggest usage of existing FastAPI features (Dependency Injection, `BackgroundTasks`, etc.) consistent with best practices.

