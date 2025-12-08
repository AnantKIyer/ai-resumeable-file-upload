"""
FastAPI application entry point with upload endpoints.
"""
import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import (
    InitUploadRequest,
    InitUploadResponse,
    ChunkUploadResponse,
    UploadStatusResponse,
    CompleteUploadResponse
)
from .storage import Storage
from .upload_service import UploadService
from .ai_integration import AIIntegration

# Initialize FastAPI app
app = FastAPI(
    title="Resumable AI File Upload API",
    description="API for resumable chunked file uploads with AI integration",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
# Use environment variables if set, otherwise use defaults (relative to backend dir)
UPLOADS_DIR = os.getenv("UPLOADS_DIR")
COMPLETED_DIR = os.getenv("COMPLETED_DIR")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1024 * 1024))  # 1MB default

storage = Storage(uploads_dir=UPLOADS_DIR, completed_dir=COMPLETED_DIR)
upload_service = UploadService(storage=storage, chunk_size=CHUNK_SIZE)
ai_integration = AIIntegration()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Resumable AI File Upload API",
        "version": "1.0.0",
        "endpoints": {
            "init": "POST /api/upload/init",
            "chunk": "POST /api/upload/chunk",
            "status": "GET /api/upload/status/{uploadId}",
            "complete": "POST /api/upload/complete/{uploadId}"
        }
    }


@app.post("/api/upload/init", response_model=InitUploadResponse)
async def init_upload(request: InitUploadRequest):
    """
    Initialize a new upload session.
    
    Returns uploadId and chunkSize for chunked uploads.
    """
    try:
        upload_id, chunk_size = upload_service.init_upload(request)
        return InitUploadResponse(
            uploadId=upload_id,
            chunkSize=chunk_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize upload: {str(e)}")


@app.post("/api/upload/chunk", response_model=ChunkUploadResponse)
async def upload_chunk(
    uploadId: str = Form(...),
    chunkIndex: int = Form(...),
    totalChunks: int = Form(...),
    chunk: UploadFile = File(...)
):
    """
    Upload a single chunk.
    
    This endpoint is idempotent - uploading the same chunk multiple times
    will not cause duplication or corruption.
    """
    try:
        # Read chunk data
        chunk_data = await chunk.read()
        
        # Upload chunk with idempotency
        success, received_count, message = upload_service.upload_chunk(
            upload_id=uploadId,
            chunk_index=chunkIndex,
            chunk_data=chunk_data,
            total_chunks=totalChunks
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return ChunkUploadResponse(
            success=True,
            receivedChunks=received_count,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload chunk: {str(e)}")


@app.get("/api/upload/status/{upload_id}", response_model=UploadStatusResponse)
async def get_upload_status(upload_id: str):
    """
    Get the status of an upload session.
    
    Returns which chunks have been received, enabling resume functionality.
    """
    try:
        status = upload_service.get_upload_status(upload_id)
        if status is None:
            raise HTTPException(status_code=404, detail=f"Upload session {upload_id} not found")
        
        # Handle partial status (when session not in memory)
        if status.get("total_chunks") is None:
            # Try to infer from storage
            received_chunks = status.get("received_chunks", [])
            if received_chunks:
                # Estimate total chunks (this is a limitation - in production, store in DB)
                estimated_total = max(received_chunks) + 1
                return UploadStatusResponse(
                    uploadId=upload_id,
                    totalChunks=estimated_total,
                    receivedChunks=received_chunks,
                    isComplete=len(received_chunks) == estimated_total
                )
            else:
                raise HTTPException(status_code=404, detail=f"Upload session {upload_id} not found")
        
        return UploadStatusResponse(
            uploadId=status["upload_id"],
            totalChunks=status["total_chunks"],
            receivedChunks=status["received_chunks"],
            isComplete=status["is_complete"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get upload status: {str(e)}")


@app.post("/api/upload/complete/{upload_id}", response_model=CompleteUploadResponse)
async def complete_upload(upload_id: str):
    """
    Complete an upload by reassembling all chunks.
    
    This endpoint:
    1. Validates all chunks are present
    2. Reassembles the file
    3. Runs AI integration hooks (validation, scanning, metadata)
    4. Triggers downstream jobs if applicable
    """
    try:
        # Complete upload and get file path + metadata
        result = upload_service.complete_upload(upload_id)
        if result is None:
            raise HTTPException(status_code=400, detail="Failed to complete upload")
        
        file_path, metadata = result
        
        # AI Integration: Validate dataset/artifact
        is_valid, validation_error = ai_integration.validate_dataset(
            file_path, metadata.fileType
        )
        if not is_valid:
            # Clean up invalid file
            file_path.unlink()
            raise HTTPException(status_code=400, detail=f"Validation failed: {validation_error}")
        
        # AI Integration: Schema validation
        schema_valid, schema_error = ai_integration.validate_schema(file_path, metadata.fileType)
        if not schema_valid:
            file_path.unlink()
            raise HTTPException(status_code=400, detail=f"Schema validation failed: {schema_error}")
        
        # AI Integration: Security scanning
        is_safe, scan_error, scan_results = ai_integration.scan_file(file_path)
        if not is_safe:
            file_path.unlink()
            raise HTTPException(status_code=400, detail=f"Security scan failed: {scan_error}")
        
        # AI Integration: Generate enhanced metadata
        enhanced_metadata = ai_integration.generate_metadata(file_path, upload_id, metadata)
        
        # AI Integration: Register in dataset registry
        if metadata.fileType == 'dataset':
            ai_integration.register_dataset(upload_id, enhanced_metadata)
        
        # AI Integration: Trigger downstream jobs
        downstream_job_id = None
        if metadata.fileType == 'dataset':
            # Trigger fine-tuning pipeline
            downstream_job_id = ai_integration.notify_fine_tuning_pipeline(
                file_path, enhanced_metadata
            )
            # Trigger data curation
            ai_integration.notify_data_curation_system(file_path, enhanced_metadata)
        elif metadata.fileType == 'model_artifact':
            # Could trigger model evaluation pipeline
            pass
        
        return CompleteUploadResponse(
            success=True,
            filepath=str(file_path),
            metadata=metadata,
            downstreamJobId=downstream_job_id,
            message="Upload completed successfully"
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete upload: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

