# Cloud2BIM Async Web Service

A FastAPI-based web service that processes 3D point cloud files (PTX, XYZ, or PLY format) and a YAML configuration to generate structured BIM models in IFC format. Based on the open-source [Cloud2BIM](https://github.com/aronfothi/Cloud2BIM) project, this service segments building elements such as slabs, walls, and openings, and returns both an IFC file and a point-to-element index mapping.

---

## 🚀 Features

* Accepts `.ptx`, `.xyz`, and `.ply` point cloud formats
* Automatically converts multiple point cloud files to PLY format for processing
* Uses Cloud2BIM segmentation logic
* Asynchronous processing with job tracking
* YAML-based configurable pipeline
* REST API with progress reporting
* Outputs:

  * IFC model file (`.ifc`)
  * JSON file mapping IFC elements to point indices
* Includes a CLI client tool

---

## 🚪 Requirements

* Python 3.10+
* pip
* Optional: BlenderBIM or other IFC viewer for result validation

---

## 📂 Installation

```bash
git clone <your-repository-url> # Replace with your actual repository URL
cd Cloud2BIM_web
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

The easiest way to run the application is using Docker Compose:

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Using Docker directly

You can also build and run the Docker container manually:

```bash
# Build the Docker image
docker build -t cloud2bim .

# Run the container
docker run -p 8001:8001 -v $(pwd)/jobs:/app/jobs --name cloud2bim cloud2bim
```

The API will be accessible at http://localhost:8001/docs

---

## 🚪 Run the Server

```bash
# Option 1: Using Python directly
uvicorn app.main:app --reload --port 8005

# Option 2: Using the main.py script
python main.py
```

Visit [http://localhost:8005/docs](http://localhost:8005/docs) for Swagger UI when using Option 1,
or [http://localhost:8001/docs](http://localhost:8001/docs) when using Option 2 or Docker.

---

## 🚼 API Endpoints

| Endpoint                               | Method | Description                                                                 |
| -------------------------------------- | ------ | --------------------------------------------------------------------------- |
| `/convert`                             | POST   | Upload point cloud file (PLY format) and config file, initiates conversion. |
| `/status/{job_id}`                     | GET    | Check job progress, status, current stage, and any error messages.          |
| `/results/{job_id}/model.ifc`          | GET    | Download the generated IFC model file for a completed job.                  |
| `/results/{job_id}/point_mapping.json` | GET    | Download the JSON file mapping IFC elements to point indices for a completed job. |

---

## 💪 Example Usage (CLI Client)

```bash
python client/client.py tests/data/scan6.ptx tests/data/sample_config.yaml --server_url http://localhost:8005 --output_dir ./output
```

This command will:
1. Upload `scan6.ptx` and `sample_config.yaml` to the server.
2. Poll the server for job status updates.
3. Once the job is complete, download `model.ifc` and `point_mapping.json` to the `./output/` directory, prefixed with the job ID.

---

## 📊 Output Structure

Each job creates a folder under `jobs/<job_id>/` containing:

* `input/`  - Original uploaded point cloud and configuration files.
* `output/` - Generated `model.ifc` and `point_mapping.json` files.
* `job_status.json` - Contains the current status, progress, and stage of the job.

---

## 🛠️ Development

See `developer-guide.md` (to be created) for full development instructions.

### Setup Linting and Formatting

It's recommended to use `black` for code formatting and `flake8` for linting.

```bash
pip install black flake8
# To format
black .
# To lint
flake8 .
```

---

## 🚫 Limitations

* No authentication or file size limits
* No automatic cleanup of old jobs
* Limited to single-instance async workers (no Celery)

---

## 🚪 Contributing

Contributions are welcome! Please open an issue or PR.

---

## 📑 License

MIT License — see `LICENSE` file for details.

---

## 🌐 Credits

Built using [Cloud2BIM](https://github.com/aronfothi/Cloud2BIM) and [IfcOpenShell](http://ifcopenshell.org/).

---

Happy building 🏠🚀
