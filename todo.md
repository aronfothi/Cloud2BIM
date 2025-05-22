# Definition of Done (DoD): Cloud2BIM Async Web Service

This document defines the criteria for completing each component of the project. A task is considered “Done” only if it meets all the corresponding acceptance criteria listed below.

---

## 📦 1. Project Setup

- [x] Project initialized in a version-controlled Git repository.
- [x] Python virtual environment (`.venv`) is created and activated.
- [x] Dependencies listed in `requirements.txt` and successfully installed.
- [x] Directory structure includes `app/`, `client/`, `.github/`, `jobs/`, and test data folders.
- [x] `.gitignore` includes common Python artifacts and job output folders.

---

## 🧠 2. Copilot Integration

- [x] `.github/copilot-instructions.md` exists and:
  - [x] Explains the project context clearly.
  - [x] Includes rules for coding standards, tech stack, naming, async patterns.
  - [x] Provides expected behavior for endpoint generation and background task logic.

---

## 🌍 3. FastAPI Web Service

### ✅ 3.1 `/convert` Endpoint

- [x] Accepts `.ptx` or `.xyz` point cloud and `.yaml` config as multipart upload.
- [x] Generates a UUID job ID and stores input files in `jobs/<job_id>/input/`.
- [x] Validates file types, responds with 202 and job ID.
- [x] Spawns a background task (non-blocking) to begin processing.

### ✅ 3.2 `/status/{job_id}` Endpoint

- [x] Accepts valid job ID.
- [x] Returns job metadata including:
  - [x] Status: `pending`, `running`, `completed`, or `failed`.
  - [x] Progress: integer percentage.
  - [x] Current processing stage (e.g., “Wall Detection”).
  - [x] Error message if applicable.
- [x] Returns `404` for unknown job IDs.

### ✅ 3.3 `/results/{job_id}/model.ifc`

- [x] Returns binary IFC file for completed jobs.
- [x] Uses `StreamingResponse` or `FileResponse`.
- [x] Validates job completion and file existence before serving.

### ✅ 3.4 `/results/{job_id}/point_mapping.json`

- [x] Returns JSON file mapping IFC elements to point indices.
- [x] Includes error handling for missing or incomplete jobs.

---

## 🧰 4. Background Processing Logic

- [x] YAML config is parsed and validated.
- [x] PTX or XYZ file is read and converted into internal point cloud format (using Open3D).
- [x] Refactored `app/core/cloud2entities.py` into a class-based `CloudToBimProcessor`.
- [ ] `CloudToBimProcessor` class methods are invoked to:
  - [x] Detect slabs, walls, openings (initial implementation done, needs refinement and full integration within the class).
  - [ ] Detect zones (method within `CloudToBimProcessor`).
  - [ ] Generate IFC file using IfcOpenShell (method within `CloudToBimProcessor`, needs actual entity creation).
- [x] After each step:
  - [x] Progress percentage and current stage are updated.
- [x] Outputs are saved in `jobs/<job_id>/output/`:
  - [x] `model.ifc` (placeholder, needs actual generation)
  - [x] `point_mapping.json` (placeholder, needs actual generation)
- [x] Job tracker updated to `completed` on success, `failed` on exception.

---

## 🖥️ 5. CLI Client

- [ ] Accepts CLI arguments for one or more point cloud files (PLY, PTX, XYZ), a config file, and server URL.
- [ ] Merges multiple point cloud files into a single Open3D PointCloud object.
- [ ] Converts the merged point cloud to a standard format (e.g., PLY) before upload.
- [ ] Uploads the merged point cloud file and config file via `POST /convert`.
- [x] Polls `GET /status/{job_id}` until job is complete.
- [x] Prints progress percentage and stage name to stdout.
- [x] Downloads IFC and mapping files on completion.
- [x] Saves output with filenames prefixed by job ID.

---

## 🧪 6. Testing & Validation

### ✅ 6.1 Basic Unit Tests
- [x] Unit tests or manual test scripts for each endpoint (basic structure created, needs expansion).
- [ ] Sample project (input + config + output) added for demonstration (`tests/data/`).

### 🆕 6.2 CloudToBimProcessor Tests
- [ ] Create comprehensive test suite for `CloudToBimProcessor` class:
  - [ ] Test initialization with various config options
  - [ ] Test point cloud loading for different formats (PLY, PTX, XYZ)
  - [ ] Test slab detection
  - [ ] Test wall and opening detection
  - [ ] Test zone identification
  - [ ] Test IFC model generation
  - [ ] Test error handling and edge cases
  - [ ] Test progress tracking and logging
  - [ ] Test point mapping file generation
- [ ] Add test fixtures for sample point clouds and configs
- [ ] Set up mock objects for external dependencies
- [ ] Test with corrupted/invalid input files

### 🆕 6.3 Point Cloud Merging Tests
- [ ] Create test suite for point cloud merging functionality:
  - [ ] Test merging multiple PLY files
  - [ ] Test merging multiple PTX files
  - [ ] Test merging mixed format files (PLY + PTX + XYZ)
  - [ ] Test handling of color data during merging
  - [ ] Test coordinate system alignment
  - [ ] Test error handling for invalid files
  - [ ] Test memory usage with large point clouds

### ✅ 6.4 Integration Tests
- [ ] IFC output opened and verified in at least one BIM viewer (e.g., BlenderBIM).
- [ ] Mapping file manually checked against known point cloud.
- [ ] Test end-to-end workflow with merged point clouds
- [ ] Performance testing with large datasets

### 🆕 6.5 Client Tests
- [ ] Test client-side file format detection
- [ ] Test point cloud merging error handling
- [ ] Test progress reporting
- [ ] Test connection error handling
- [ ] Test large file upload handling

---

## 🧹 7. Quality and Maintenance

- [ ] All Python code follows PEP8 with consistent formatting (run `black .` and `flake8 .`).
- [ ] Type hints are present for all functions and parameters.
- [ ] All public functions have docstrings.
- [ ] Logging is implemented using `logging` module, not `print()`.
- [ ] Dead code and debugging statements removed.
- [x] Update `README.md` with current project status and instructions.
- [ ] Create `developer-guide.md`.

---

## 🚀 8. Deployment Readiness

- [ ] Resolve any outstanding dependency issues.
- [ ] Verify application runs correctly with at least two different point cloud samples producing valid IFC models.
- [ ] Consider Dockerization for easier deployment.

---

## 🐛 Known Issues / TODOs from Implementation

- `app/core/job_processor.py`: 
    - Ensure `config_params` are correctly passed and used by detection/generation functions.
    - Implement robust error handling for each processing stage.
- `app/core/cloud2entities.py`:
    - Refine `detect_walls`, `detect_slabs`, `detect_openings` for accuracy and robustness.
    - Implement `detect_zones`.
    - Ensure point indices are correctly managed and returned for `point_mapping.json`.
- `app/core/generate_ifc.py`:
    - Replace placeholder IFC generation with actual IfcOpenShell logic to create entities based on detected elements.
    - Implement mapping of detected elements to IFC entities.
    - Store point indices per IFC element for `point_mapping.json`.
- `app/main.py` / `app/api/endpoints.py`:
    - Review error handling and HTTP status codes for all endpoints.
- General:
    - Ensure thread-safety if any shared mutable state is introduced (currently `jobs` dict in `endpoints.py` is accessed by background tasks).
    - Add more detailed logging throughout the application.

