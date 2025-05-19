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
  - Explains the project context clearly.
  - Includes rules for coding standards, tech stack, naming, async patterns.
  - Provides expected behavior for endpoint generation and background task logic.

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
- [ ] PTX or XYZ file is read and converted into internal point cloud format.
- [ ] Cloud2BIM logic is invoked to:
  - [ ] Detect slabs, walls, openings, and zones.
  - [ ] Generate IFC file using IfcOpenShell.
- [x] After each step:
  - [x] Progress percentage and current stage are updated.
- [x] Outputs are saved in `jobs/<job_id>/output/`:
  - [x] `model.ifc`
  - [x] `point_mapping.json`
- [x] Job tracker updated to `completed` on success, `failed` on exception.

---

## 🖥️ 5. CLI Client

- [x] Accepts CLI arguments for point cloud file, config file, and server URL.
- [x] Uploads files via `POST /convert`.
- [x] Polls `GET /status/{job_id}` until job is complete.
- [x] Prints progress percentage and stage name to stdout.
- [x] Downloads IFC and mapping files on completion.
- [x] Saves output with filenames prefixed by job ID.

---

## 🧪 6. Testing & Validation

- [x] Unit tests or manual test scripts for each endpoint.
- [ ] IFC output opened and verified in at least one BIM viewer.
- [ ] Mapping file manually checked against known point cloud.
- [x] Sample project (input + config + output) added for demonstration.

---

## 🧹 7. Quality and Maintenance

- [ ] All Python code follows PEP8 with consistent formatting.
- [ ] Type hints are present for all functions and parameters.
- [ ] All public functions have docstrings.
- [ ] Logging is implemented using `logging` module, not `print()`.
- [ ] Dead code and debugging statements removed.
- [ ] Repository includes:
  - `README.md` with installation, usage, API docs.
  - `TODO.md` for development tracking.
  - `copilot-instructions.md` for AI pair programming.
  - Example input files in `/data/` or `/samples/`.

---

## 🚀 8. Ready for Deployment

- [ ] Project runs locally with `uvicorn app.main:app --reload`.
- [ ] `requirements.txt` supports installation on new machines.
- [ ] Outputs are verified for at least 2 different point cloud samples.
- [ ] Optional: Dockerfile added for reproducible builds.

---

**NOTE:** Every checkbox must be checked and validated by code review or integration testing before the project is considered complete.

