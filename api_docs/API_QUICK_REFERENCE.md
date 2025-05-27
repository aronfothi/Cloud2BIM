# Cloud2BIM API Quick Reference

## Essential Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service info |
| `POST` | `/submit` | Submit job |
| `GET` | `/status/{job_id}` | Check status |
| `GET` | `/results/{job_id}/model.ifc` | Download IFC |
| `GET` | `/api/progress/{job_id}/stream` | SSE progress |

## Quick Integration Examples

### cURL
```bash
# Submit job
curl -X POST "http://localhost:8000/submit" \
  -F "point_cloud_file=@scan.ptx" \
  -F "config_file=@config.yaml"

# Check status
curl "http://localhost:8000/status/{job_id}"

# Download result
curl -O "http://localhost:8000/results/{job_id}/model.ifc"
```

### Python (Minimal)
```python
import requests

# Submit
files = {'point_cloud_file': open('scan.ptx', 'rb'), 
         'config_file': open('config.yaml', 'rb')}
job = requests.post('http://localhost:8000/submit', files=files).json()

# Monitor
while True:
    status = requests.get(f"http://localhost:8000/status/{job['job_id']}").json()
    if status['status'] == 'completed': break
    time.sleep(2)

# Download
ifc = requests.get(f"http://localhost:8000/results/{job['job_id']}/model.ifc")
with open('model.ifc', 'wb') as f: f.write(ifc.content)
```

### JavaScript (Minimal)
```javascript
// Submit
const formData = new FormData();
formData.append('point_cloud_file', pointCloudFile);
formData.append('config_file', configFile);

const job = await fetch('/submit', {method: 'POST', body: formData}).then(r => r.json());

// Monitor with SSE
const eventSource = new EventSource(`/api/progress/${job.job_id}/stream`);
eventSource.onmessage = e => {
    const data = JSON.parse(e.data);
    console.log(`${data.progress.percentage}% - ${data.progress.stage_description}`);
    if (data.status === 'completed') eventSource.close();
};
```

## Configuration Template

```yaml
# config.yaml
pc_resolution: 0.002
preprocessing:
  voxel_size: 0.002
  noise_threshold: 0.02
detection:
  grid_coefficient: 5
min_wall_length: 0.10
min_wall_thickness: 0.05
max_wall_thickness: 0.75
ifc:
  project_name: "My Project"
```

## Response Examples

### Job Submission (202)
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job submitted successfully",
  "progress": 0
}
```

### Status Check (200)
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000", 
  "status": "processing",
  "message": "Detecting walls",
  "stage": "wall_detection",
  "progress": 65
}
```

### SSE Progress Event
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing", 
  "progress": {
    "percentage": 45,
    "stage_description": "Detecting walls and openings",
    "estimated_remaining": "00:02:30"
  },
  "performance": {
    "cpu_percent": 78.5,
    "memory_percent": 42.1
  }
}
```

## Supported Formats

**Input**: PTX, XYZ, PLY  
**Output**: IFC, JSON mapping

## Status Values

- `pending` → `processing` → `completed`
- `pending` → `processing` → `failed`

## Integration Checklist

### Basic Integration
- [ ] Submit job via `/submit` endpoint
- [ ] Poll status via `/status/{job_id}`
- [ ] Download results from `/results/{job_id}/model.ifc`

### Advanced Integration
- [ ] Implement SSE for real-time progress
- [ ] Add error handling for all API calls
- [ ] Handle file upload validation
- [ ] Implement timeout and retry logic

### Production Ready
- [ ] Add authentication (API keys)
- [ ] Implement rate limiting
- [ ] Add logging and monitoring
- [ ] Configure CORS properly
- [ ] Use HTTPS in production

## Common Patterns

```python
# File validation
def validate_file(filepath):
    allowed = ['.ptx', '.xyz', '.ply']
    return any(filepath.lower().endswith(ext) for ext in allowed)

# Retry logic
import time
def retry_api_call(func, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise e
            time.sleep(2 ** attempt)  # Exponential backoff
```

For complete documentation, see [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
