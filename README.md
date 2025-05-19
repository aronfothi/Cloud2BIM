# Cloud2BIM Async Web Service

A FastAPI-based web service that processes 3D point cloud files (PTX or XYZ format) and a YAML configuration to generate structured BIM models in IFC format. Based on the open-source [Cloud2BIM](https://github.com/aronfothi/Cloud2BIM) project, this service segments building elements such as slabs, walls, and openings, and returns both an IFC file and a point-to-element index mapping.

---

## 🚀 Features

* Accepts `.ptx` and `.xyz` point cloud formats
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

* Python 3.9+
* pip
* Optional: BlenderBIM or other IFC viewer for result validation

---

## 📂 Installation

```bash
git clone https://github.com/<your-org>/cloud2bim-service.git
cd cloud2bim-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 🚪 Run the Server

```bash
uvicorn app.main:app --reload
```

Visit [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger UI.

---

## 🚼 API Endpoints

| Endpoint                               | Method | Description                         |
| -------------------------------------- | ------ | ----------------------------------- |
| `/convert`                             | POST   | Upload point cloud and config files |
| `/status/{job_id}`                     | GET    | Check job progress                  |
| `/results/{job_id}/model.ifc`          | GET    | Download the generated IFC file     |
| `/results/{job_id}/point_mapping.json` | GET    | Download point index mapping        |

---

## 💪 Example Usage (CLI Client)

```bash
python client/upload_client.py \
  --pointcloud data/building.ptx \
  --config data/config.yaml \
  --server http://localhost:8000
```

Outputs:

* `job_id.ifc`
* `job_id_point_mapping.json`

---

## 📊 Output Structure

Each job creates a folder under `jobs/<job_id>/` containing:

* `input/`  - Original uploaded files
* `output/` - Generated IFC and mapping results

---

## 🛠️ Development

See `developer-guide.md` for full development instructions.

### Setup Linting and Formatting

```bash
pip install black flake8
black app/
flake8 app/
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
