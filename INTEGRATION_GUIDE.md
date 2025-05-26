# Cloud2BIM Integration Guide

## Overview

Cloud2BIM is a web service that converts 3D point cloud files into IFC BIM models. This guide provides everything you need to integrate Cloud2BIM into your application.

## Quick Start (5 minutes)

1. **Start the service**: `uvicorn main:app --host 0.0.0.0 --port 8000`
2. **Submit a job**: Upload PTX/XYZ/PLY file + config via `/submit` 
3. **Monitor progress**: Use `/api/progress/{job_id}/stream` for real-time updates
4. **Download results**: Get IFC model from `/results/{job_id}/model.ifc`

## Minimal Working Example

```python
import requests

# Submit job
files = {
    'point_cloud_file': open('scan.ptx', 'rb'),
    'config_file': open('config.yaml', 'rb')
}
response = requests.post('http://localhost:8000/submit', files=files)
job_id = response.json()['job_id']

# Wait for completion
import time
while True:
    status = requests.get(f'http://localhost:8000/status/{job_id}').json()
    print(f"Progress: {status.get('progress', {}).get('percentage', 0)}%")
    if status['status'] == 'completed':
        break
    time.sleep(3)

# Download result
ifc = requests.get(f'http://localhost:8000/results/{job_id}/model.ifc')
with open('model.ifc', 'wb') as f:
    f.write(ifc.content)
```

## API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST /submit` | Upload point cloud file + config | Submit conversion job |
| `POST /convert` | Upload JSON point cloud + config | Submit JSON data job |
| `GET /status/{job_id}` | Get job status | Poll for updates |
| `GET /api/progress/{job_id}/stream` | SSE stream | Real-time progress |
| `GET /results/{job_id}/model.ifc` | Download IFC | Get final model |
| `GET /results/{job_id}/point_mapping.json` | Download mapping | Get point associations |

## File Formats

### Input Formats
- **PTX**: Leica point cloud format (recommended for large scans)
- **XYZ**: ASCII format with X,Y,Z coordinates
- **PLY**: Polygon file format with optional colors
- **JSON**: Structured point cloud data

### Output Formats
- **IFC**: Industry Foundation Classes BIM model
- **JSON**: Point-to-element mapping data

## Configuration File (config.yaml)

```yaml
# Essential settings
pc_resolution: 0.002          # Point cloud resolution
preprocessing:
  voxel_size: 0.002           # Downsampling size
  noise_threshold: 0.02       # Noise removal threshold
detection:
  grid_coefficient: 5         # Detection grid size

# Wall detection
min_wall_length: 0.10         # Minimum wall length (meters)
min_wall_thickness: 0.05      # Minimum wall thickness
max_wall_thickness: 0.75      # Maximum wall thickness

# IFC metadata
ifc:
  project_name: "My Building"
  building_name: "Main Building"
  site_name: "Construction Site"
```

## Progress Tracking

### Polling Method (Simple)
```python
def poll_progress(job_id):
    while True:
        status = requests.get(f'http://localhost:8000/status/{job_id}').json()
        progress = status.get('progress', {})
        print(f"{progress.get('percentage', 0)}% - {progress.get('stage_description', 'Processing')}")
        
        if status['status'] in ['completed', 'failed']:
            return status
        time.sleep(2)
```

### Server-Sent Events (Real-time)
```javascript
const eventSource = new EventSource(`/api/progress/${jobId}/stream`);
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`${data.progress.percentage}% - ${data.progress.stage_description}`);
    
    if (data.status === 'completed') {
        eventSource.close();
        downloadResults(jobId);
    }
};
```

## Processing Stages

The conversion process includes these stages:

1. **Initializing** - Job setup and validation
2. **Loading Point Cloud** - Reading and parsing input file
3. **Preprocessing** - Noise removal and downsampling
4. **Detecting Slabs** - Finding floor/ceiling surfaces
5. **Detecting Walls** - Identifying wall structures
6. **Detecting Openings** - Finding doors and windows
7. **Detecting Zones** - Room/space identification
8. **Generating IFC** - Creating BIM model
9. **Finalizing** - Saving results

## Error Handling

### HTTP Status Codes
- `200`: Success
- `202`: Job accepted (async processing)
- `400`: Bad request (invalid input)
- `404`: Job or file not found
- `422`: Validation error
- `500`: Server error

### Common Error Scenarios
```python
def handle_api_response(response):
    if response.status_code == 202:
        return response.json()['job_id']
    elif response.status_code == 400:
        print("Invalid input - check file format and config")
    elif response.status_code == 422:
        print("File validation failed - unsupported format")
    elif response.status_code == 500:
        print("Server error - try again later")
    else:
        print(f"Unexpected error: {response.status_code}")
    return None
```

## Performance Guidelines

### File Size Recommendations
- **Small files** (<10MB): Process in seconds
- **Medium files** (10-100MB): Process in 1-5 minutes  
- **Large files** (100MB-1GB): Process in 5-30 minutes
- **Very large files** (>1GB): May require special handling

### Optimization Tips
1. **Downsample** large point clouds before upload
2. **Use PTX format** for better compression
3. **Adjust voxel_size** in config for faster processing
4. **Monitor memory usage** for very large files

## Integration Patterns

### Batch Processing
```python
def process_multiple_files(file_pairs):
    jobs = []
    for pc_file, config_file in file_pairs:
        job_id = submit_job(pc_file, config_file)
        jobs.append(job_id)
    
    # Monitor all jobs
    while jobs:
        for job_id in jobs[:]:  # Copy list to modify during iteration
            status = get_status(job_id)
            if status['status'] == 'completed':
                download_results(job_id)
                jobs.remove(job_id)
        time.sleep(5)
```

### Web Application Integration
```javascript
class PointCloudConverter {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async convertFile(pointCloudFile, configFile, onProgress) {
        // Submit job
        const formData = new FormData();
        formData.append('point_cloud_file', pointCloudFile);
        formData.append('config_file', configFile);
        
        const response = await fetch(`${this.baseUrl}/submit`, {
            method: 'POST',
            body: formData
        });
        
        const { job_id } = await response.json();
        
        // Stream progress
        return new Promise((resolve, reject) => {
            const eventSource = new EventSource(`${this.baseUrl}/api/progress/${job_id}/stream`);
            
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                onProgress(data);
                
                if (data.status === 'completed') {
                    eventSource.close();
                    resolve(job_id);
                } else if (data.status === 'failed') {
                    eventSource.close();
                    reject(new Error(data.message || 'Conversion failed'));
                }
            };
            
            eventSource.onerror = reject;
        });
    }
}
```

## Production Deployment

### Docker Deployment
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables
```bash
# Set in production
export CLOUD2BIM_MAX_FILE_SIZE=1073741824  # 1GB
export CLOUD2BIM_JOB_TIMEOUT=3600          # 1 hour
export CLOUD2BIM_STORAGE_PATH=/data/jobs
export CLOUD2BIM_LOG_LEVEL=INFO
```

### Security Considerations
1. **File Upload Limits**: Restrict file sizes and types
2. **Input Validation**: Validate all uploaded files
3. **API Rate Limiting**: Prevent abuse
4. **HTTPS**: Use SSL/TLS in production
5. **Authentication**: Implement API keys or OAuth

## Troubleshooting

### Common Issues

1. **Job stuck in pending**
   - Check server logs for processing errors
   - Verify file format is supported
   - Ensure sufficient memory/disk space

2. **Upload fails**
   - Check file size limits
   - Verify file format (PTX, XYZ, PLY only)
   - Ensure config.yaml is valid

3. **Processing timeout**
   - Large files may need longer timeout
   - Consider downsampling point cloud
   - Check server resources

4. **SSE connection drops**
   - Implement reconnection logic
   - Add error handling for network issues
   - Fall back to polling if needed

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed API logging
response = requests.post(url, files=files)
print(f"Response: {response.status_code}")
print(f"Headers: {response.headers}")
print(f"Body: {response.text}")
```

## Support Resources

- **API Documentation**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **Quick Reference**: [API_QUICK_REFERENCE.md](./API_QUICK_REFERENCE.md)
- **OpenAPI Spec**: [openapi.yaml](./openapi.yaml)
- **Example Clients**: [client/](./client/) directory

## Example Applications

Check these working examples:
- `client/enhanced_client.py` - Full-featured Python client
- `enhanced_client_ptx.py` - PTX file processor
- `static/progress_monitor.html` - Web-based monitor

Start with the minimal example above, then explore these for advanced features.
