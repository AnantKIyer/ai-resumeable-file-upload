# Resumable AI File Upload System

A production-ready, full-stack resumable file upload system designed specifically for AI workloads. This system enables reliable upload of large datasets, model artifacts, and training files with robust error handling, resume capability, and AI-specific integration hooks.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Backend Design](#backend-design)
- [API Strategy](#api-strategy)
- [Frontend Design](#frontend-design)
- [AI Integration](#ai-integration)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Testing](#testing)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

## Overview

The Resumable AI File Upload System is built to handle the unique requirements of AI data ingestion:

- **Large Files**: Supports files from kilobytes to gigabytes
- **Network Resilience**: Automatically resumes interrupted uploads
- **Parallel Processing**: Uploads chunks concurrently for optimal performance
- **AI-Specific**: Built-in hooks for fine-tuning pipelines, data curation, and validation
- **Production-Ready**: Comprehensive error handling, idempotency, and monitoring

### Use Cases

- **Training Dataset Upload**: Upload large JSONL, CSV, or Parquet datasets for model training
- **Model Artifact Storage**: Upload PyTorch, TensorFlow, or ONNX model files
- **Evaluation Data**: Upload test sets and validation data
- **Data Curation**: Upload raw data for labeling and preprocessing pipelines

## Features

### Core Upload Features

#### 1. **Chunked Upload**

- Files are automatically split into 1MB chunks (configurable)
- Enables efficient transfer and resume capability
- Reduces memory footprint on both client and server

#### 2. **Parallel Uploads**

- Multiple chunks uploaded concurrently (default: 5 parallel)
- Configurable concurrency for optimal network utilization
- Automatic load balancing across chunks

#### 3. **Resume Capability**

- Automatic resume on network failures
- Server-side state tracking
- Client-side localStorage persistence (optional)
- Intelligent chunk detection - only missing chunks are re-uploaded

#### 4. **Idempotent Operations**

- Safe to retry failed chunks
- No duplicate data on re-upload
- Atomic chunk storage prevents corruption

#### 5. **Progress Tracking**

- Real-time upload progress (percentage)
- Chunk-level status visualization
- Upload speed and ETA calculation
- Failed chunk identification and retry

### AI-Specific Features

#### 1. **Dataset Validation**

- Format validation (JSONL, CSV, Parquet)
- Schema validation hooks
- File type detection (dataset vs model artifact)

#### 2. **Security Scanning**

- Virus scanning integration points
- PII (Personally Identifiable Information) detection hooks
- Content validation before acceptance

#### 3. **Metadata Generation**

- Automatic metadata extraction
- File type detection
- Checksum calculation
- Lineage tracking for data governance

#### 4. **Pipeline Integration**

- Fine-tuning pipeline triggers
- Data curation system integration
- Downstream job queuing
- Webhook support for external systems

## Architecture

### System Overview

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   React UI      │         │   FastAPI       │         │   Filesystem    │
│   Frontend      │◄───────►│   Backend       │◄───────►│   Storage       │
└─────────────────┘         └─────────────────┘         └─────────────────┘
       │                            │                              │
       │                            │                              │
       ▼                            ▼                              ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  localStorage   │         │  Upload Service  │         │  AI Integration │
│  (State Cache)  │         │  (Session Mgmt)  │         │  (Hooks)        │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

### Component Architecture

#### Frontend Components

- **FileUploader**: Main upload component with drag-and-drop
- **UploadProgress**: Real-time progress visualization
- **ChunkManager**: File splitting and state management
- **UploadService**: Parallel upload orchestration

#### Backend Services

- **Storage Layer**: Filesystem abstraction for chunk storage
- **Upload Service**: Session management and chunk coordination
- **AI Integration**: Validation, metadata, and pipeline hooks
- **API Layer**: RESTful endpoints with FastAPI

## Backend Design

### Technology Stack

- **Framework**: FastAPI (Python 3.8+)
- **Storage**: Filesystem (extensible to S3, GCS, Azure Blob)
- **Validation**: Pydantic models
- **Async Support**: Uvicorn ASGI server

### Core Components

#### 1. Storage Layer (`app/storage.py`)

The storage layer provides an abstraction for chunk storage and file reassembly:

```python
class Storage:
    - store_chunk(): Atomic chunk storage with retry logic
    - get_chunk(): Retrieve chunk by index
    - list_chunks(): Get all received chunk indices
    - reassemble_file(): Concatenate chunks into final file
    - cleanup_chunks(): Remove temporary chunks
```

**Key Features**:

- Atomic writes: Temp file → rename pattern prevents corruption
- Race condition handling: Retry logic for concurrent operations
- Idempotent: Safe to store same chunk multiple times
- Directory management: Automatic creation with error handling

#### 2. Upload Service (`app/upload_service.py`)

Manages upload sessions and coordinates chunk processing:

```python
class UploadService:
    - init_upload(): Create new upload session
    - upload_chunk(): Process chunk with idempotency
    - get_upload_status(): Return session state
    - complete_upload(): Reassemble and validate file
```

**Session Management**:

- In-memory session tracking (extensible to database)
- Chunk state tracking (received, missing, failed)
- Automatic session cleanup after completion
- Resume support from storage state

#### 3. AI Integration (`app/ai_integration.py`)

Provides hooks for AI-specific processing:

```python
class AIIntegration:
    - validate_dataset(): Format and schema validation
    - generate_metadata(): Extract file metadata
    - scan_file(): Security scanning (virus, PII)
    - notify_fine_tuning_pipeline(): Trigger downstream jobs
    - register_dataset(): Add to dataset registry
```

**Integration Points**:

- Validation: Custom schema checking
- Metadata: File type, size, checksum, lineage
- Security: Placeholder for ClamAV, Presidio integration
- Pipelines: Celery/RQ job queuing hooks

### Data Flow

#### Upload Flow

1. **Initialization**

   ```
   Client → POST /api/upload/init
   Server → Creates session, returns uploadId + chunkSize
   ```

2. **Chunk Upload**

   ```
   Client → POST /api/upload/chunk (parallel)
   Server → Stores chunk atomically, updates session
   ```

3. **Status Check** (optional, for resume)

   ```
   Client → GET /api/upload/status/{uploadId}
   Server → Returns received chunk indices
   ```

4. **Completion**
   ```
   Client → POST /api/upload/complete/{uploadId}
   Server → Validates, reassembles, runs AI hooks, returns metadata
   ```

### Error Handling

- **Network Failures**: Client retries with exponential backoff
- **Server Errors**: Descriptive error messages, safe to retry
- **Validation Failures**: Clear error messages, file cleanup
- **Concurrent Conflicts**: Idempotent operations prevent corruption

## API Strategy

### RESTful API Design

All endpoints follow REST principles with clear resource naming:

```
/api/upload/init          → Initialize upload session
/api/upload/chunk         → Upload individual chunk
/api/upload/status/{id}   → Get upload status
/api/upload/complete/{id} → Complete and reassemble
```

### Endpoint Details

#### POST /api/upload/init

**Purpose**: Initialize a new upload session

**Request**:

```json
{
  "filename": "training_data.jsonl",
  "totalSize": 52428800,
  "checksum": "optional-sha256-hash"
}
```

**Response**:

```json
{
  "uploadId": "550e8400-e29b-41d4-a716-446655440000",
  "chunkSize": 1048576
}
```

**Strategy**:

- Creates unique upload session
- Calculates total chunks needed
- Returns chunk size for client coordination
- Session stored in memory (extensible to database)

#### POST /api/upload/chunk

**Purpose**: Upload a single chunk (idempotent)

**Request** (multipart/form-data):

```
uploadId: "550e8400-..."
chunkIndex: "0"
totalChunks: "50"
chunk: <binary data>
```

**Response**:

```json
{
  "success": true,
  "receivedChunks": 5,
  "message": "Chunk uploaded successfully"
}
```

**Strategy**:

- **Idempotency**: Check if chunk exists before writing
- **Atomic Storage**: Temp file → rename pattern
- **Concurrent Safe**: Directory creation with retry
- **Validation**: Verify chunk index within bounds

#### GET /api/upload/status/{uploadId}

**Purpose**: Get upload status for resume capability

**Response**:

```json
{
  "uploadId": "550e8400-...",
  "totalChunks": 50,
  "receivedChunks": [0, 1, 2, 3, 5, 10, 11],
  "isComplete": false
}
```

**Strategy**:

- Enables intelligent resume
- Client only uploads missing chunks
- Server reconstructs state from storage
- Fast lookup for status checks

#### POST /api/upload/complete/{uploadId}

**Purpose**: Complete upload and trigger processing

**Response**:

```json
{
  "success": true,
  "filepath": "completed/training_data.jsonl",
  "metadata": {
    "uploadId": "550e8400-...",
    "filename": "training_data.jsonl",
    "size": 52428800,
    "fileType": "dataset",
    "timestamp": "2024-01-01T12:00:00"
  },
  "downstreamJobId": "fine-tuning-job-123"
}
```

**Strategy**:

- Validates all chunks present
- Reassembles file in order
- Runs AI integration hooks
- Triggers downstream jobs
- Returns comprehensive metadata

### API Design Principles

1. **Idempotency**: All chunk operations are idempotent
2. **Stateless**: Each request contains all necessary context
3. **Resumable**: Status endpoint enables resume without re-init
4. **Error Recovery**: Clear error messages enable client retry
5. **Performance**: Parallel chunk uploads maximize throughput

### Client-Side Upload Strategy

#### Chunking Strategy

```javascript
// File split into 1MB chunks
const chunks = splitFile(file, chunkSize);

// Parallel upload with concurrency limit
const uploadQueue = missingChunks.map((chunkIndex) =>
  uploadChunk(uploadId, chunkIndex, chunks[chunkIndex])
);

// Process with concurrency control
await processUploadQueue(uploadQueue, (maxConcurrent = 5));
```

#### Resume Strategy

1. **On Init**: Check server status

   ```javascript
   const serverStatus = await getUploadStatus(uploadId);
   chunkState.mergeServerState(serverStatus.receivedChunks);
   ```

2. **Identify Missing**: Calculate missing chunks

   ```javascript
   const missing = chunkState.getMissingChunks();
   ```

3. **Upload Only Missing**: Skip already-received chunks
   ```javascript
   await uploadChunks(missing);
   ```

#### Retry Strategy

- **Exponential Backoff**: 1s, 2s, 4s delays
- **Max Retries**: 3 attempts per chunk
- **Failed Chunk Tracking**: Mark for manual retry
- **Continue on Failure**: Other chunks continue uploading

## Frontend Design

### Technology Stack

- **Framework**: React 18 with hooks
- **Build Tool**: Vite
- **HTTP Client**: Axios
- **File Handling**: react-dropzone
- **State Management**: React hooks + localStorage

### Component Architecture

#### FileUploader Component

Main upload interface with drag-and-drop:

```jsx
<FileUploader>
  - File selection (drag-and-drop or click) - Upload initiation - Progress
  display - Error handling - Resume capability
</FileUploader>
```

**Features**:

- Drag-and-drop file selection
- File validation (size, type)
- Upload state management
- Auto-resume on page reload
- Error display and retry

#### UploadProgress Component

Real-time progress visualization:

```jsx
<UploadProgress>
  - Overall progress bar - Chunk status grid - Upload speed and ETA - Failed
  chunk indicators
</UploadProgress>
```

**Visualization**:

- Progress percentage
- Chunk grid (green=uploaded, yellow=in-progress, red=failed)
- Upload statistics (speed, ETA)
- Failed chunk warnings

### State Management

#### ChunkState Class

Tracks upload progress:

```javascript
class ChunkState {
  uploaded: Set<number>      // Successfully uploaded chunks
  failed: Set<number>        // Failed chunks
  inProgress: Set<number>    // Currently uploading

  markUploaded(index)
  markFailed(index)
  getMissingChunks()
  mergeServerState(serverChunks)
}
```

#### LocalStorage Persistence

Optional state persistence:

```javascript
// Save state
saveStateToLocalStorage(uploadId, chunkState, filename, size);

// Load state
const state = loadStateFromLocalStorage(uploadId);

// Clear on completion
clearStateFromLocalStorage(uploadId);
```

## AI Integration

### Integration Points

#### 1. Fine-Tuning Pipeline

After dataset upload completes:

```python
def notify_fine_tuning_pipeline(filepath, metadata):
    # Example: Celery integration
    task = fine_tuning_queue.enqueue(
        process_fine_tuning_dataset,
        filepath=str(filepath),
        metadata=metadata
    )
    return task.id
```

**Use Cases**:

- Trigger fine-tuning jobs
- Queue preprocessing tasks
- Start training pipelines

#### 2. Data Curation System

Register datasets for labeling:

```python
def notify_data_curation_system(filepath, metadata):
    # Example: Labelbox integration
    dataset = labeling_platform.create_dataset(
        name=metadata['filename'],
        filepath=filepath
    )
    return dataset.uid
```

**Use Cases**:

- Register in labeling platforms
- Trigger data quality checks
- Start validation pipelines

#### 3. Validation Hooks

Custom validation logic:

```python
def validate_dataset(filepath, file_type):
    if file_type == 'dataset':
        # Check JSONL format
        # Validate schema
        # Check required fields
        return is_valid, error_message
```

**Validation Types**:

- Format validation (JSONL, CSV structure)
- Schema validation (required fields)
- Data type validation
- Size limits

#### 4. Security Scanning

Security checks before acceptance:

```python
def scan_file(filepath):
    # Virus scanning (ClamAV)
    virus_result = scan_virus(filepath)

    # PII detection (Presidio)
    pii_result = detect_pii(filepath)

    return is_safe, error, scan_results
```

**Security Features**:

- Virus/malware scanning
- PII detection and redaction
- Content policy enforcement
- Compliance checks

#### 5. Metadata & Lineage

Track data provenance:

```python
metadata = {
    "uploadId": "uuid",
    "filename": "dataset.jsonl",
    "size": 52428800,
    "checksum": "sha256-hash",
    "fileType": "dataset",
    "lineage": {
        "source": "user_upload",
        "downstream_jobs": ["fine-tuning-123"]
    }
}
```

**Lineage Tracking**:

- Upload → Processing → Model artifacts
- Data catalog integration
- Compliance and audit trails

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend runs on `http://localhost:3000`

### Quick Test

1. Open `http://localhost:3000` in browser
2. Drag and drop a file (or click to select)
3. Click "Start Upload"
4. Watch progress in real-time
5. File completes and triggers AI hooks

## Configuration

### Backend Environment Variables

```bash
# Storage directories
UPLOADS_DIR=uploads          # Temporary chunk storage
COMPLETED_DIR=completed      # Completed file storage

# Chunk size (bytes)
CHUNK_SIZE=1048576           # 1MB default
```

### Frontend Environment Variables

Create `.env` in frontend directory:

```env
VITE_API_URL=http://localhost:8000
```

### Chunk Size Tuning

**Small Files (< 10MB)**:

- Chunk size: 512KB
- Concurrency: 3

**Medium Files (10MB - 100MB)**:

- Chunk size: 1MB (default)
- Concurrency: 5

**Large Files (> 100MB)**:

- Chunk size: 2MB
- Concurrency: 10

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run specific categories
pytest -m unit           # Unit tests
pytest -m api            # API tests
pytest -m integration    # Integration tests
pytest -m stress         # Stress tests

# With coverage
pytest --cov=app --cov-report=html
```

**Test Coverage**:

- Unit tests: 50+ tests
- API tests: 30+ tests
- Integration tests: 6+ tests
- Stress tests: 8+ tests
- Performance tests: 10+ tests

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Watch mode
npm test -- --watch

# With coverage
npm run test:coverage

# E2E tests
npm run test:e2e
```

## Production Deployment

### Backend Deployment

#### Option 1: Gunicorn + Uvicorn

```bash
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

#### Option 2: Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Deployment

```bash
# Build for production
npm run build

# Serve with nginx
# Copy dist/ to nginx html directory
```

### Production Considerations

#### Storage

Replace filesystem with object storage:

```python
# S3 example
import boto3
s3_client = boto3.client('s3')
s3_client.upload_fileobj(chunk_data, bucket, f"{upload_id}/{chunk_index}.chunk")
```

#### Session Persistence

Use database for sessions:

```python
# PostgreSQL example
session = {
    "upload_id": upload_id,
    "filename": filename,
    "total_chunks": total_chunks,
    "received_chunks": [...],
    "created_at": datetime.utcnow()
}
db.sessions.insert_one(session)
```

#### Security

- Add authentication (JWT, OAuth2)
- Enable HTTPS
- Implement rate limiting
- Add CORS restrictions
- Enable actual virus scanning

#### Monitoring

- Add Prometheus metrics
- Structured logging (JSON)
- Error tracking (Sentry)
- Performance monitoring

## Troubleshooting

### Common Issues

#### Upload Fails Immediately

**Symptoms**: Upload fails right after starting

**Solutions**:

- Check backend is running on port 8000
- Verify CORS configuration
- Check browser console for errors
- Verify API URL in frontend `.env`

#### Resume Not Working

**Symptoms**: Upload doesn't resume after page reload

**Solutions**:

- Check server status endpoint is working
- Verify localStorage is enabled
- Check uploadId is persisted correctly
- Verify server state reconstruction

#### Slow Uploads

**Symptoms**: Uploads are slower than expected

**Solutions**:

- Increase chunk size (if network allows)
- Increase concurrency limit
- Check network connection
- Verify server isn't overwhelmed

#### Chunk Storage Errors

**Symptoms**: "Error storing chunk" messages

**Solutions**:

- Check disk space
- Verify directory permissions
- Check for race conditions (reduce concurrency)
- Review storage layer logs

### Debug Mode

Enable debug logging:

```python
# Backend
import logging
logging.basicConfig(level=logging.DEBUG)
```

```javascript
// Frontend
localStorage.setItem("debug", "true");
```

## API Documentation

Interactive API documentation available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

MIT License - see LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions:

- Open an issue on GitHub
- Check existing documentation
- Review test cases for examples

---

**Built for AI workloads. Designed for reliability. Ready for production.**
