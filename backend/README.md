# Backend - Resumable AI File Upload API

FastAPI backend for resumable chunked file uploads with AI integration hooks.

## Setup

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### POST /api/upload/init

Initialize a new upload session.

**Request Body:**
```json
{
  "filename": "training_data.jsonl",
  "totalSize": 52428800,
  "checksum": "optional-sha256-checksum"
}
```

**Response:**
```json
{
  "uploadId": "550e8400-e29b-41d4-a716-446655440000",
  "chunkSize": 1048576
}
```

### POST /api/upload/chunk

Upload a single chunk. This endpoint is **idempotent** - uploading the same chunk multiple times is safe.

**Content-Type:** `multipart/form-data`

**Form Fields:**
- `uploadId` (string): Upload session identifier
- `chunkIndex` (int): Zero-based chunk index
- `totalChunks` (int): Total number of chunks
- `chunk` (file): Binary chunk data

**Response:**
```json
{
  "success": true,
  "receivedChunks": 5,
  "message": "Chunk uploaded successfully"
}
```

### GET /api/upload/status/{uploadId}

Get the current status of an upload session, including which chunks have been received. This enables resume functionality.

**Response:**
```json
{
  "uploadId": "550e8400-e29b-41d4-a716-446655440000",
  "totalChunks": 50,
  "receivedChunks": [0, 1, 2, 3, 4, 5, 10, 11, 12],
  "isComplete": false
}
```

### POST /api/upload/complete/{uploadId}

Complete an upload by reassembling all chunks into the final file. This endpoint:
1. Validates all chunks are present
2. Reassembles the file
3. Runs AI integration hooks (validation, scanning, metadata generation)
4. Triggers downstream jobs if applicable

**Response:**
```json
{
  "success": true,
  "filepath": "completed/training_data.jsonl",
  "metadata": {
    "uploadId": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "training_data.jsonl",
    "size": 52428800,
    "checksum": "sha256-hash",
    "timestamp": "2024-01-01T12:00:00",
    "fileType": "dataset",
    "filepath": "completed/training_data.jsonl"
  },
  "downstreamJobId": "fine-tuning-job-123",
  "message": "Upload completed successfully"
}
```

## AI Integration Hooks

The backend includes integration points in `app/ai_integration.py`:

### 1. Dataset Validation

```python
is_valid, error = ai_integration.validate_dataset(filepath, file_type)
```

**Current Implementation:**
- Checks file extension (JSONL, CSV, Parquet, etc.)
- Validates JSONL format (one JSON object per line)

**Production Integration:**
- Add schema validation (check required fields)
- Validate data types and ranges
- Check for missing values
- Verify label distributions

### 2. Schema Validation

```python
is_valid, error = ai_integration.validate_schema(filepath, file_type)
```

**Production Integration:**
- For fine-tuning datasets: verify `messages` or `prompt` fields
- For classification: check `text` and `label` fields
- Validate data types and constraints

### 3. Security Scanning

```python
is_safe, error, results = ai_integration.scan_file(filepath)
```

**Current Implementation:**
- Placeholder for virus scanning
- Placeholder for PII detection

**Production Integration:**
- Integrate ClamAV for virus scanning
- Use Presidio or spaCy for PII detection
- Scan for sensitive patterns (SSN, credit cards, etc.)

### 4. Fine-Tuning Pipeline Integration

```python
job_id = ai_integration.notify_fine_tuning_pipeline(filepath, metadata)
```

**Production Integration:**
```python
# Example with Celery
from celery import Celery

celery_app = Celery('fine_tuning')

def notify_fine_tuning_pipeline(filepath, metadata):
    task = celery_app.send_task(
        'process_fine_tuning_dataset',
        args=[str(filepath)],
        kwargs={'metadata': metadata}
    )
    return task.id
```

### 5. Data Curation System Integration

```python
dataset_id = ai_integration.notify_data_curation_system(filepath, metadata)
```

**Production Integration:**
```python
# Example with Labelbox
import labelbox

def notify_data_curation_system(filepath, metadata):
    client = labelbox.Client(api_key=os.getenv('LABELBOX_API_KEY'))
    dataset = client.create_dataset(name=metadata['filename'])
    # Upload file to Labelbox
    return dataset.uid
```

### 6. Metadata Generation

```python
enhanced_metadata = ai_integration.generate_metadata(filepath, upload_id, metadata)
```

**Generated Metadata:**
- File size, checksum, timestamp
- File type detection (dataset, model_artifact, archive)
- Estimated record count (for datasets)
- Framework detection (for model artifacts)
- Lineage tracking information

## Storage Architecture

### Chunk Storage

Chunks are stored in: `uploads/{uploadId}/{chunkIndex}.chunk`

- Atomic writes: chunks are written to temp files then renamed
- Idempotent: existing chunks are not overwritten
- Cleanup: chunks are removed after successful reassembly

### Completed Files

Completed files are stored in: `completed/{filename}`

### Production Storage Options

Replace filesystem storage with:

1. **Object Storage (S3, GCS, Azure Blob)**
   ```python
   # Example S3 integration
   import boto3
   
   s3_client = boto3.client('s3')
   s3_client.upload_fileobj(chunk_data, bucket, f"{upload_id}/{chunk_index}.chunk")
   ```

2. **Distributed Cache (Redis)**
   ```python
   # For small chunks, store in Redis
   redis_client.setex(
       f"chunk:{upload_id}:{chunk_index}",
       3600,  # TTL
       chunk_data
   )
   ```

3. **Database for Session Metadata**
   ```python
   # Store session info in PostgreSQL/MongoDB
   session = {
       "upload_id": upload_id,
       "filename": filename,
       "total_chunks": total_chunks,
       "received_chunks": [...],
       "created_at": datetime.utcnow()
   }
   db.sessions.insert_one(session)
   ```

## Error Handling

- **400 Bad Request**: Invalid request data, missing chunks
- **404 Not Found**: Upload session not found
- **500 Internal Server Error**: Server-side errors

All errors include descriptive messages for debugging.

## Configuration

Environment variables:

- `UPLOADS_DIR`: Temporary chunk storage directory (default: `uploads`)
- `COMPLETED_DIR`: Completed file storage directory (default: `completed`)
- `CHUNK_SIZE`: Chunk size in bytes (default: `1048576` = 1MB)

## Testing

```bash
# Run with pytest (if tests are added)
pytest

# Test API endpoints manually
curl -X POST http://localhost:8000/api/upload/init \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.jsonl", "totalSize": 1024}'
```

## Production Deployment

1. **Use a production ASGI server:**
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

2. **Add authentication:**
   - JWT tokens
   - OAuth2
   - API keys

3. **Enable HTTPS:**
   - Use reverse proxy (nginx, Traefik)
   - Configure SSL certificates

4. **Add monitoring:**
   - Prometheus metrics
   - Structured logging
   - Error tracking (Sentry)

5. **Scale horizontally:**
   - Use shared storage (S3, NFS)
   - Use distributed session store (Redis)
   - Load balance with nginx/HAProxy

