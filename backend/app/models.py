"""
Pydantic models for API requests and responses.
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID


class InitUploadRequest(BaseModel):
    """Request model for initializing an upload session."""
    filename: str = Field(..., description="Name of the file being uploaded")
    totalSize: int = Field(..., gt=0, description="Total size of the file in bytes")
    checksum: Optional[str] = Field(None, description="Optional checksum for file validation")


class InitUploadResponse(BaseModel):
    """Response model for upload initialization."""
    uploadId: str = Field(..., description="Unique identifier for this upload session")
    chunkSize: int = Field(..., description="Size of each chunk in bytes")


class ChunkUploadRequest(BaseModel):
    """Request model for uploading a chunk (metadata only, binary data comes via FormData)."""
    uploadId: str = Field(..., description="Upload session identifier")
    chunkIndex: int = Field(..., ge=0, description="Zero-based index of this chunk")
    totalChunks: int = Field(..., gt=0, description="Total number of chunks for this upload")


class ChunkUploadResponse(BaseModel):
    """Response model for chunk upload."""
    success: bool = Field(..., description="Whether the chunk was successfully stored")
    receivedChunks: int = Field(..., description="Number of chunks received so far")
    message: str = Field(..., description="Status message")


class UploadStatusResponse(BaseModel):
    """Response model for upload status check."""
    uploadId: str = Field(..., description="Upload session identifier")
    totalChunks: int = Field(..., description="Total number of chunks expected")
    receivedChunks: List[int] = Field(..., description="List of chunk indices that have been received")
    isComplete: bool = Field(..., description="Whether all chunks have been received")


class FileMetadata(BaseModel):
    """Metadata about a completed upload."""
    uploadId: str = Field(..., description="Upload session identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    checksum: Optional[str] = Field(None, description="File checksum if provided")
    timestamp: str = Field(..., description="Upload completion timestamp")
    fileType: str = Field(..., description="Detected file type")
    filepath: str = Field(..., description="Path to the completed file")


class CompleteUploadResponse(BaseModel):
    """Response model for upload completion."""
    success: bool = Field(..., description="Whether the upload was successfully completed")
    filepath: str = Field(..., description="Path to the reassembled file")
    metadata: FileMetadata = Field(..., description="File metadata")
    downstreamJobId: Optional[str] = Field(None, description="Optional downstream job identifier if triggered")
    message: str = Field(..., description="Completion message")

