# Developer Guide: Cloud2BIM Asynchronous Web Service

Welcome to the developer guide for the **Cloud2BIM async service**, a FastAPI-based web application that converts PTX/XYZ point clouds into structured IFC models using the Cloud2BIM segmentation logic.

---

## 📁 Project Structure

```
cloud2bim-service/
├── app/                      # FastAPI application code
│   ├── main.py              # App entry point and route setup
│   ├── api.py               # API endpoints
│   ├── worker.py            # Background processing logic
│   ├── models.py            # Pydantic models for requests/responses
│   ├── cloud2bim_wrapper.py # Interface to Cloud2BIM segmentation
├── client/                   # CLI tool
│   └── upload_client.py     # Command-line uploader and downloader
├── jobs/                     # Input/output storage for jobs
│   └── <uuid>/              # Each job's unique folder
│       ├── input/
│       └── output/
├── .github/
│   └── copilot-instructions.md
├── requirements.txt          # Python dependencies
├── README.md                 # Project overview and instructions
├── developer-guide.md        # ← This file
└── todo.md / definition-of-done.md
```

---

## 🧱 Prerequisites

* Python 3.9 or newer
* pip / virtualenv
* Git
* IFC viewer (e.g. BlenderBIM) for validating outputs
* (Optional) Docker, Redis if scaling in the future

---

## 🚀 Setup Guide

### 1. Clone and Install

```bash
git clone https://github.com/<your-org>/cloud2bim-service.git
cd cloud2bim-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the Service

```bash
uvicorn app.main:app --reload
```

API will be available at: [http://localhost:8000](http://localhost:8000)

Swagger UI (API docs): [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Run the CLI Client

```bash
python client/upload_client.py --pointcloud data/building.ptx --config config.yaml
```

---

## ⚙️ Development Guidelines

### API Design

| Endpoint                               | Method | Description                      |
| -------------------------------------- | ------ | -------------------------------- |
| `/convert`                             | POST   | Upload point cloud + YAML config |
| `/status/{job_id}`                     | GET    | Poll job status and progress     |
| `/results/{job_id}/model.ifc`          | GET    | Download resulting IFC file      |
| `/results/{job_id}/point_mapping.json` | GET    | Download point index mapping     |

All endpoints are non-blocking. Use `/status` to track long-running jobs.

### Code Organization

* **`main.py`**: Entry point, sets up FastAPI and includes routes.
* **`api.py`**: Defines `/convert`, `/status`, and result download routes.
* **`worker.py`**: Handles background processing, updates job state.
* **`cloud2bim_wrapper.py`**: Encapsulates Cloud2BIM logic.
* **`jobs/`**: Contains job-specific data.

  * `/input/` – uploaded `.ptx` or `.xyz` and config `.yaml`
  * `/output/` – generated `model.ifc` and `point_mapping.json`

### Adding a New Feature

1. Create a branch:

   ```bash
   git checkout -b feature/my-feature
   ```
2. Add code with tests or example usage if applicable.
3. Run and test:

   ```bash
   uvicorn app.main:app --reload
   ```
4. Push and open a pull request.

### Updating Cloud2BIM

If Cloud2BIM changes significantly:

* Update `cloud2bim_wrapper.py` with new logic or parameters.
* Ensure any breaking changes in input/output handling are addressed.
* Run integration tests with real `.ptx` and `.xyz` files.

---

## 📅 Background Job Handling

* Jobs are stored in memory during runtime in a dictionary:

```python
jobs = {
  "<job_id>": {
    "status": "running",
    "progress": 50,
    "current_stage": "wall_detection",
    "result": {
      "ifc_path": "...",
      "mapping_path": "..."
    }
  }
}
```

* Future: migrate to Redis/Celery for scaling and persistent job queues.

### Progress Reporting

Update job progress using:

```python
jobs[job_id]['progress'] = 40
jobs[job_id]['current_stage'] = "wall_detection"
```

Call this after each segmentation step.

---

## 📊 Testing

* Use small `.xyz` files for fast local tests.
* Check `/status/{job_id}` until `status == completed`.
* Open resulting `model.ifc` in BlenderBIM or similar.
* Validate that point index mapping matches IFC elements.

---

## 🛠️ Tools and Tips

* Use [FastAPI docs](https://fastapi.tiangolo.com) for reference.
* Use `curl` or [httpie](https://httpie.io/) for manual endpoint testing.
* Use a linter like `flake8` or formatter like `black`:

  ```bash
  pip install flake8 black
  black app/
  ```

---

## 🧹 Cleanup

* Use a script or cron to delete jobs older than X days.
* Optional: Add `GET /cleanup/{job_id}` for admin cleanup.

---

## 🔐 Security (To Consider)

* File size limits (to prevent DoS via large uploads)
* Validate content type before parsing files
* Prevent path traversal in file reads
* Consider API keys or tokens for authentication (future)

---

## 📩 FAQ

**Q: Why async?**
To allow long-running segmentation jobs without blocking API clients.

**Q: Why polling?**
Simpler than WebSockets, sufficient for job status updates.

**Q: How big can my point cloud be?**
Depends on memory and disk limits. Try to stay below a few hundred MB per file in local mode.

---

## 📬 Contact & Contributions

Please open issues or pull requests if you'd like to improve the project.
For architecture questions, contact the original maintainer or consult the `README.md`.

---

Happy developing! 🚀

```
```
