# Cloud2BIM API Documentation

## Overview

The Cloud2BIM service is a RESTful API that converts 3D point cloud files into IFC (Industry Foundation Classes) BIM models using advanced segmentation algorithms. The service provides real-time progress tracking and supports multiple point cloud formats.

**Base URL**: `http://localhost:8000` (or your deployment URL)

**API Version**: 1.0.0

## Quick Start

1. **Upload** a point cloud file (PTX, XYZ, or PLY) and configuration
2. **Monitor** progress using Server-Sent Events or polling
3. **Download** the generated IFC model and point mapping

## Authentication

Currently, no authentication is required. The API is designed for internal use or trusted environments.

## Supported File Formats

### Input Formats
- **PTX**: Leica point cloud format
- **XYZ**: ASCII point cloud format  
- **PLY**: Polygon File Format

### Output Formats
- **IFC**: Industry Foundation Classes BIM model
- **JSON**: Point-to-element mapping data

## Endpoints

### 1. Service Information

#### `GET /`

Get basic service information and available endpoints.

**Response:**
```json
{
  "service": "Cloud2BIM Service",
  "version": "1.0.0",
  "description": "Async point cloud to IFC BIM model conversion service with real-time progress tracking",
  "endpoints": {
    "submit": "/submit",
    "convert": "/convert",
    "status": "/status/{job_id}",
    "results": "/results/{job_id}/model.ifc",
    "point_mapping": "/results/{job_id}/point_mapping.json",
    "stream_progress": "/api/progress/{job_id}/stream",
    "stream_basic": "/api/progress/{job_id}/stream/basic"
  }
}
```

---

### 2. Submit Conversion Job (File Upload)

#### `POST /submit`

Submit a point cloud file for conversion to IFC format. This endpoint accepts common point cloud file formats.

**Content-Type**: `multipart/form-data`

**Parameters:**
- `point_cloud_file` (file, required): Point cloud file (PTX, XYZ, or PLY format)
- `config_file` (file, required): YAML configuration file

**Response**: `202 Accepted`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job submitted successfully",
  "stage": "initializing",
  "progress": {
    "percentage": 0,
    "stage": "initializing",
    "stage_description": "Initializing job...",
    "current_operation": null,
    "processed_items": 0,
    "total_items": 0,
    "estimated_remaining_seconds": null,
    "processing_speed": null
  }
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/submit" \
  -F "point_cloud_file=@scan.ptx" \
  -F "config_file=@config.yaml"
```

---

### 3. Submit Conversion Job (JSON Data)

#### `POST /convert`

Submit a new point cloud conversion job.

**Content-Type**: `multipart/form-data`

**Parameters:**
- `point_cloud_file` (file, required): Point cloud file (PTX, XYZ, or PLY)
- `config_file` (file, required): YAML configuration file

**Response**: `202 Accepted`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job submitted successfully",
  "stage": "queued",
  "progress": 0
}
```

**Example Configuration File** (`config.yaml`):
```yaml
dilute: false
dilution_factor: 10
exterior_scan: false
pc_resolution: 0.002
preprocessing:
  voxel_size: 0.002
  noise_threshold: 0.02
detection:
  grid_coefficient: 5

bfs_thickness: 0.3
tfs_thickness: 0.4

min_wall_length: 0.10
min_wall_thickness: 0.05
max_wall_thickness: 0.75
exterior_walls_thickness: 0.3

ifc:
  project_name: "My Building Project"
```

**Example cURL:**
```bash
curl -X POST "http://localhost:8000/convert" \
  -F "point_cloud_file=@building_scan.ptx" \
  -F "config_file=@config.yaml"
```

**Example Python:**
```python
import requests

with open('building_scan.ptx', 'rb') as pc_file, \
     open('config.yaml', 'rb') as config_file:
    
    files = {
        'point_cloud_file': pc_file,
        'config_file': config_file
    }
    
    response = requests.post('http://localhost:8000/convert', files=files)
    job_data = response.json()
    job_id = job_data['job_id']
```

---

### 3. Check Job Status

#### `GET /status/{job_id}`

Get the current status of a conversion job.

**Parameters:**
- `job_id` (path, required): UUID of the job

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Detecting walls and openings",
  "stage": "wall_detection",
  "progress": 65
}
```

**Status Values:**
- `pending`: Job is queued
- `processing`: Job is being processed
- `completed`: Job finished successfully
- `failed`: Job failed with error

**Example:**
```bash
curl "http://localhost:8000/status/550e8400-e29b-41d4-a716-446655440000"
```

---

### 5. Download Results

#### `GET /results/{job_id}/model.ifc`

Download the generated IFC BIM model.

**Parameters:**
- `job_id` (path, required): UUID of the completed job

**Response**: Binary IFC file

**Example:**
```bash
curl -O "http://localhost:8000/results/550e8400-e29b-41d4-a716-446655440000/model.ifc"
```

#### `GET /results/{job_id}/point_mapping.json`

Download the point-to-element mapping data.

**Parameters:**
- `job_id` (path, required): UUID of the completed job

**Response**: JSON mapping file
```json
{
  "total_points": 2777608,
  "mapped_points": 2456789,
  "elements": [
    {
      "element_id": "wall_001",
      "element_type": "IfcWall",
      "point_indices": [1, 2, 3, 156, 157, 158],
      "point_count": 125678
    }
  ]
}
```

---

### 6. Real-Time Progress Monitoring

#### Server-Sent Events (SSE)

For real-time progress updates without polling.

#### `GET /api/progress/{job_id}/stream`

Stream detailed progress information using Server-Sent Events.

**Parameters:**
- `job_id` (path, required): UUID of the job to monitor

**Headers:**
- `Accept: text/event-stream`

**Event Types:**
- `progress`: Progress update
- `error`: Error occurred
- `complete`: Job completed

**Example Event Data:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": {
    "percentage": 45,
    "stage": "wall_detection",
    "stage_description": "Detecting walls and openings",
    "estimated_remaining": "00:02:30",
    "processing_speed": "15000 points/sec"
  },
  "performance": {
    "cpu_percent": 78.5,
    "memory_percent": 42.1,
    "memory_used_mb": 1024
  },
  "timestamp": "2025-05-26T10:30:45Z"
}
```

**JavaScript Example:**
```javascript
const eventSource = new EventSource('/api/progress/550e8400-e29b-41d4-a716-446655440000/stream');

eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log(`Progress: ${data.progress.percentage}%`);
    console.log(`Stage: ${data.progress.stage_description}`);
};

eventSource.onerror = function(event) {
    console.error('SSE error:', event);
    eventSource.close();
};
```

#### `GET /api/progress/{job_id}/stream/basic`

Stream basic progress percentage using Server-Sent Events.

**Example Event:**
```
event: progress
data: 45

event: complete
data: completed
```

---

## Complete Workflow Example

### Python Integration

```python
import requests
import time
import sseclient
import json

class Cloud2BIMClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def submit_job(self, point_cloud_path, config_path):
        """Submit a conversion job"""
        with open(point_cloud_path, 'rb') as pc_file, \
             open(config_path, 'rb') as config_file:
            
            files = {
                'point_cloud_file': pc_file,
                'config_file': config_file
            }
            
            response = self.session.post(f"{self.base_url}/submit", files=files)
            
            if response.status_code == 202:
                return response.json()['job_id']
            else:
                raise Exception(f"Job submission failed: {response.text}")
    
    def monitor_with_sse(self, job_id):
        """Monitor job progress with SSE"""
        sse_url = f"{self.base_url}/api/stream/progress/{job_id}"
        response = requests.get(sse_url, stream=True, headers={'Accept': 'text/event-stream'})
        
        if response.status_code != 200:
            return self.monitor_with_polling(job_id)  # Fallback
        
        client = sseclient.SSEClient(response)
        
        for event in client.events():
            if event.data:
                data = json.loads(event.data)
                
                if event.event == "error":
                    raise Exception(data.get('error', 'Unknown error'))
                
                progress = data.get('progress', {})
                percentage = progress.get('percentage', 0)
                stage = progress.get('stage_description', 'Processing')
                
                print(f"Progress: {percentage}% - {stage}")
                
                if percentage >= 100 or data.get('status') == 'completed':
                    return True
                elif data.get('status') == 'failed':
                    raise Exception("Job failed")
    
    def monitor_with_polling(self, job_id):
        """Monitor job progress with polling"""
        while True:
            response = self.session.get(f"{self.base_url}/status/{job_id}")
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                progress = data.get('progress', 0)
                
                print(f"Progress: {progress}% - Status: {status}")
                
                if status == 'completed':
                    return True
                elif status == 'failed':
                    raise Exception(f"Job failed: {data.get('message')}")
            
            time.sleep(2)  # Poll every 2 seconds
    
    def download_results(self, job_id, output_dir="results"):
        """Download IFC model and mapping"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Download IFC file
        ifc_response = self.session.get(f"{self.base_url}/results/{job_id}/model.ifc")
        if ifc_response.status_code == 200:
            ifc_path = os.path.join(output_dir, f"{job_id}_model.ifc")
            with open(ifc_path, 'wb') as f:
                f.write(ifc_response.content)
            print(f"IFC downloaded: {ifc_path}")
        
        # Download mapping
        mapping_response = self.session.get(f"{self.base_url}/results/{job_id}/point_mapping.json")
        if mapping_response.status_code == 200:
            mapping_path = os.path.join(output_dir, f"{job_id}_mapping.json")
            with open(mapping_path, 'w') as f:
                f.write(mapping_response.text)
            print(f"Mapping downloaded: {mapping_path}")
        
        return ifc_path, mapping_path

# Usage Example
client = Cloud2BIMClient()

# Submit job
job_id = client.submit_job("building_scan.ptx", "config.yaml")
print(f"Job submitted: {job_id}")

# Monitor progress
try:
    client.monitor_with_sse(job_id)  # Try SSE first
except:
    client.monitor_with_polling(job_id)  # Fallback to polling

# Download results
ifc_file, mapping_file = client.download_results(job_id)
print(f"Conversion complete! IFC: {ifc_file}")
```

### JavaScript Integration

```javascript
class Cloud2BIMClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    async submitJob(pointCloudFile, configFile) {
        const formData = new FormData();
        formData.append('point_cloud_file', pointCloudFile);
        formData.append('config_file', configFile);

        const response = await fetch(`${this.baseUrl}/convert`, {
            method: 'POST',
            body: formData
        });

        if (response.status === 202) {
            const data = await response.json();
            return data.job_id;
        } else {
            throw new Error(`Job submission failed: ${response.statusText}`);
        }
    }

    monitorWithSSE(jobId, onProgress, onComplete, onError) {
        const eventSource = new EventSource(`${this.baseUrl}/api/stream/progress/${jobId}`);

        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.progress) {
                onProgress(data.progress.percentage, data.progress.stage_description);
            }

            if (data.status === 'completed') {
                eventSource.close();
                onComplete();
            } else if (data.status === 'failed') {
                eventSource.close();
                onError('Job failed');
            }
        };

        eventSource.onerror = function(event) {
            eventSource.close();
            onError('SSE connection failed');
        };

        return eventSource;
    }

    async downloadResults(jobId) {
        const ifcResponse = await fetch(`${this.baseUrl}/results/${jobId}/model.ifc`);
        const mappingResponse = await fetch(`${this.baseUrl}/results/${jobId}/point_mapping.json`);

        return {
            ifc: await ifcResponse.blob(),
            mapping: await mappingResponse.json()
        };
    }
}

// Usage Example
const client = new Cloud2BIMClient();

// Submit job
const jobId = await client.submitJob(pointCloudFile, configFile);
console.log(`Job submitted: ${jobId}`);

// Monitor progress
client.monitorWithSSE(
    jobId,
    (progress, stage) => console.log(`${progress}% - ${stage}`),
    async () => {
        console.log('Job completed!');
        const results = await client.downloadResults(jobId);
        // Handle results...
    },
    (error) => console.error('Error:', error)
);
```

## Error Handling

### HTTP Status Codes

- `200 OK`: Successful request
- `202 Accepted`: Job submitted successfully
- `400 Bad Request`: Invalid input data
- `404 Not Found`: Job or resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "detail": "Error description",
  "type": "validation_error",
  "loc": ["field_name"]
}
```

## Rate Limiting

Currently, no rate limiting is implemented. For production use, consider implementing appropriate rate limiting based on your requirements.

## Best Practices

1. **Always use SSE for progress monitoring** when possible, with polling as fallback
2. **Check job status** before attempting to download results
3. **Handle network timeouts** gracefully in your integration
4. **Store job IDs** for later reference and result retrieval
5. **Validate file formats** before uploading to avoid errors
6. **Use appropriate file sizes** - very large files may take significant time to process

## Configuration Parameters

### Point Cloud Processing
- `pc_resolution`: Point cloud resolution (default: 0.002)
- `dilute`: Enable point cloud dilution (default: false)
- `dilution_factor`: Factor for point dilution (default: 10)

### Detection Parameters
- `grid_coefficient`: Grid size coefficient (default: 5)
- `min_wall_length`: Minimum wall length in meters (default: 0.10)
- `min_wall_thickness`: Minimum wall thickness in meters (default: 0.05)
- `max_wall_thickness`: Maximum wall thickness in meters (default: 0.75)

### IFC Output
- `project_name`: Name for the generated IFC project

## Integration Guide for External Applications

### Authentication and Security

Currently, the API does not require authentication. For production deployment:

1. **API Keys**: Implement API key authentication in request headers
2. **Rate Limiting**: Consider implementing rate limiting (e.g., 10 requests/minute per client)
3. **HTTPS**: Use HTTPS in production environments
4. **CORS**: Configure CORS settings appropriately for your domain

### Error Handling Best Practices

```python
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

def safe_api_call(url, **kwargs):
    """Make a safe API call with proper error handling"""
    try:
        response = requests.get(url, timeout=30, **kwargs)
        response.raise_for_status()
        return response.json()
    except Timeout:
        print("Request timed out")
        return None
    except ConnectionError:
        print("Connection error - check if service is running")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print("Job not found")
        elif e.response.status_code == 500:
            print("Server error - try again later")
        else:
            print(f"HTTP error: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

### Production Deployment Considerations

1. **File Size Limits**: Configure appropriate upload limits (recommended: 500MB max)
2. **Processing Timeouts**: Set reasonable timeouts for long-running jobs (30-60 minutes)
3. **Storage Management**: Implement cleanup for old job files
4. **Load Balancing**: Use multiple instances for high-traffic scenarios
5. **Monitoring**: Monitor job queue length and processing times

### SDK Example for Different Languages

#### Python SDK Wrapper

```python
import requests
import time
import json
from typing import Optional, Dict, Any, Callable

class Cloud2BIMError(Exception):
    """Custom exception for Cloud2BIM API errors"""
    pass

class Cloud2BIMSDK:
    """Production-ready SDK for Cloud2BIM API"""
    
    def __init__(self, base_url: str = "http://localhost:8000", 
                 api_key: Optional[str] = None, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({'X-API-Key': api_key})
    
    def submit_job(self, point_cloud_path: str, config_path: str) -> str:
        """Submit a conversion job and return job ID"""
        try:
            with open(point_cloud_path, 'rb') as pc_file, \
                 open(config_path, 'rb') as config_file:
                
                files = {
                    'point_cloud_file': pc_file,
                    'config_file': config_file
                }
                
                response = self.session.post(
                    f"{self.base_url}/submit",
                    files=files,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()['job_id']
                
        except FileNotFoundError as e:
            raise Cloud2BIMError(f"File not found: {e}")
        except requests.RequestException as e:
            raise Cloud2BIMError(f"API request failed: {e}")
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get current job status"""
        try:
            response = self.session.get(
                f"{self.base_url}/status/{job_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Cloud2BIMError(f"Failed to get job status: {e}")
    
    def wait_for_completion(self, job_id: str, 
                          progress_callback: Optional[Callable] = None,
                          poll_interval: int = 3) -> Dict[str, Any]:
        """Wait for job completion with optional progress callback"""
        while True:
            status = self.get_job_status(job_id)
            
            if progress_callback:
                progress_callback(status)
            
            if status['status'] in ['completed', 'failed']:
                return status
            
            time.sleep(poll_interval)
    
    def download_results(self, job_id: str, output_dir: str) -> None:
        """Download IFC model and point mapping"""
        import os
        
        # Download IFC model
        ifc_response = self.session.get(
            f"{self.base_url}/results/{job_id}/model.ifc",
            timeout=self.timeout
        )
        ifc_response.raise_for_status()
        
        ifc_path = os.path.join(output_dir, 'model.ifc')
        with open(ifc_path, 'wb') as f:
            f.write(ifc_response.content)
        
        # Download point mapping
        mapping_response = self.session.get(
            f"{self.base_url}/results/{job_id}/point_mapping.json",
            timeout=self.timeout
        )
        mapping_response.raise_for_status()
        
        mapping_path = os.path.join(output_dir, 'point_mapping.json')
        with open(mapping_path, 'wb') as f:
            f.write(mapping_response.content)

# Usage example
def main():
    sdk = Cloud2BIMSDK(base_url="http://your-server:8000")
    
    try:
        # Submit job
        job_id = sdk.submit_job('scan.ptx', 'config.yaml')
        print(f"Job submitted: {job_id}")
        
        # Wait for completion with progress updates
        def show_progress(status):
            progress = status.get('progress', {})
            percentage = progress.get('percentage', 0)
            stage = progress.get('stage_description', 'Processing...')
            print(f"Progress: {percentage}% - {stage}")
        
        final_status = sdk.wait_for_completion(job_id, show_progress)
        
        if final_status['status'] == 'completed':
            sdk.download_results(job_id, './output')
            print("Results downloaded successfully!")
        else:
            print(f"Job failed: {final_status.get('message', 'Unknown error')}")
            
    except Cloud2BIMError as e:
        print(f"Cloud2BIM error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
```

#### JavaScript SDK

```javascript
class Cloud2BIMSDK {
    constructor(baseUrl = 'http://localhost:8000', apiKey = null) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.apiKey = apiKey;
    }
    
    async submitJob(pointCloudFile, configFile) {
        const formData = new FormData();
        formData.append('point_cloud_file', pointCloudFile);
        formData.append('config_file', configFile);
        
        const headers = {};
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }
        
        try {
            const response = await fetch(`${this.baseUrl}/submit`, {
                method: 'POST',
                body: formData,
                headers
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return data.job_id;
        } catch (error) {
            throw new Error(`Failed to submit job: ${error.message}`);
        }
    }
    
    async getJobStatus(jobId) {
        const headers = {};
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }
        
        try {
            const response = await fetch(`${this.baseUrl}/status/${jobId}`, {
                headers
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            throw new Error(`Failed to get job status: ${error.message}`);
        }
    }
    
    streamProgress(jobId, onProgress, onError = console.error, onComplete = null) {
        const url = `${this.baseUrl}/api/progress/${jobId}/stream`;
        const eventSource = new EventSource(url);
        
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                onProgress(data);
                
                if (data.status === 'completed' || data.status === 'failed') {
                    eventSource.close();
                    if (onComplete) onComplete(data);
                }
            } catch (error) {
                onError(error);
            }
        };
        
        eventSource.onerror = (error) => {
            onError(error);
            eventSource.close();
        };
        
        return eventSource; // Return for manual control
    }
    
    async downloadResults(jobId) {
        // Download both IFC and mapping files
        const [ifcResponse, mappingResponse] = await Promise.all([
            fetch(`${this.baseUrl}/results/${jobId}/model.ifc`),
            fetch(`${this.baseUrl}/results/${jobId}/point_mapping.json`)
        ]);
        
        if (!ifcResponse.ok || !mappingResponse.ok) {
            throw new Error('Failed to download results');
        }
        
        return {
            ifc: await ifcResponse.blob(),
            mapping: await mappingResponse.json()
        };
    }
}

// Usage example
async function main() {
    const sdk = new Cloud2BIMSDK('http://your-server:8000');
    
    try {
        // Get files from input elements
        const pointCloudFile = document.getElementById('pointCloudFile').files[0];
        const configFile = document.getElementById('configFile').files[0];
        
        // Submit job
        const jobId = await sdk.submitJob(pointCloudFile, configFile);
        console.log(`Job submitted: ${jobId}`);
        
        // Stream progress
        sdk.streamProgress(jobId, 
            (progress) => {
                console.log(`Progress: ${progress.progress.percentage}%`);
                // Update UI with progress
            },
            (error) => {
                console.error('Progress streaming error:', error);
            },
            async (finalStatus) => {
                if (finalStatus.status === 'completed') {
                    const results = await sdk.downloadResults(jobId);
                    
                    // Download IFC file
                    const url = URL.createObjectURL(results.ifc);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'model.ifc';
                    a.click();
                    URL.revokeObjectURL(url);
                    
                    console.log('Point mapping:', results.mapping);
                }
            }
        );
        
    } catch (error) {
        console.error('Error:', error.message);
    }
}
```

### Integration Patterns

#### Batch Processing
```python
# Process multiple files in batch
def process_batch(file_pairs, output_base_dir):
    sdk = Cloud2BIMSDK()
    jobs = []
    
    # Submit all jobs
    for pc_file, config_file in file_pairs:
        job_id = sdk.submit_job(pc_file, config_file)
        jobs.append((job_id, pc_file))
    
    # Monitor all jobs
    completed = []
    while len(completed) < len(jobs):
        for job_id, filename in jobs:
            if job_id not in [c[0] for c in completed]:
                status = sdk.get_job_status(job_id)
                if status['status'] == 'completed':
                    output_dir = f"{output_base_dir}/{job_id}"
                    os.makedirs(output_dir, exist_ok=True)
                    sdk.download_results(job_id, output_dir)
                    completed.append((job_id, filename))
                    print(f"Completed: {filename}")
        
        time.sleep(5)  # Check every 5 seconds
```

#### Web Application Integration
```javascript
// React component example
function PointCloudProcessor() {
    const [jobId, setJobId] = useState(null);
    const [progress, setProgress] = useState(null);
    const [status, setStatus] = useState('idle');
    
    const sdk = new Cloud2BIMSDK();
    
    const handleSubmit = async (files) => {
        try {
            setStatus('submitting');
            const id = await sdk.submitJob(files.pointCloud, files.config);
            setJobId(id);
            setStatus('processing');
            
            // Start progress monitoring
            sdk.streamProgress(id, 
                (progressData) => setProgress(progressData),
                (error) => {
                    console.error(error);
                    setStatus('error');
                },
                (final) => {
                    setStatus(final.status);
                    if (final.status === 'completed') {
                        // Trigger download
                        handleDownload(id);
                    }
                }
            );
        } catch (error) {
            setStatus('error');
            console.error(error);
        }
    };
    
    const handleDownload = async (id) => {
        const results = await sdk.downloadResults(id);
        // Handle download...
    };
    
    return (
        <div>
            {/* UI components */}
            {progress && (
                <div>
                    <ProgressBar value={progress.progress.percentage} />
                    <p>{progress.progress.stage_description}</p>
                </div>
            )}
        </div>
    );
}
```

## Support

For integration support or bug reports, please refer to the project documentation or contact the development team.
