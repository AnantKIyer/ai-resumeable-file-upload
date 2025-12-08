"""
Core upload service with chunk management, idempotency, and session tracking.
"""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, field

from .storage import Storage
from .models import InitUploadRequest, FileMetadata


@dataclass
class UploadSession:
    """Tracks the state of an upload session."""
    upload_id: str
    filename: str
    total_size: int
    total_chunks: int
    chunk_size: int
    checksum: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    received_chunks: set[int] = field(default_factory=set)
    
    def is_complete(self) -> bool:
        """Check if all chunks have been received."""
        return len(self.received_chunks) == self.total_chunks
    
    def get_missing_chunks(self) -> list[int]:
        """Get list of chunk indices that haven't been received yet."""
        all_chunks = set(range(self.total_chunks))
        return sorted(all_chunks - self.received_chunks)


class UploadService:
    """Manages upload sessions and chunk processing."""
    
    def __init__(self, storage: Storage, chunk_size: int = 1024 * 1024):
        """
        Initialize upload service.
        
        Args:
            storage: Storage instance for chunk operations
            chunk_size: Default chunk size in bytes (1MB default)
        """
        self.storage = storage
        self.chunk_size = chunk_size
        self.sessions: Dict[str, UploadSession] = {}
    
    def init_upload(self, request: InitUploadRequest) -> tuple[str, int]:
        """
        Initialize a new upload session.
        
        Args:
            request: Upload initialization request
            
        Returns:
            Tuple of (upload_id, chunk_size)
        """
        upload_id = str(uuid.uuid4())
        total_chunks = (request.totalSize + self.chunk_size - 1) // self.chunk_size
        
        session = UploadSession(
            upload_id=upload_id,
            filename=request.filename,
            total_size=request.totalSize,
            total_chunks=total_chunks,
            chunk_size=self.chunk_size,
            checksum=request.checksum
        )
        
        self.sessions[upload_id] = session
        return upload_id, self.chunk_size
    
    def get_session(self, upload_id: str) -> Optional[UploadSession]:
        """Get an upload session by ID."""
        return self.sessions.get(upload_id)
    
    def get_or_create_session_from_storage(self, upload_id: str) -> Optional[UploadSession]:
        """
        Reconstruct session from storage if it doesn't exist in memory.
        This enables resume after server restart.
        
        Args:
            upload_id: Upload session identifier
            
        Returns:
            UploadSession if found, None otherwise
        """
        # Check if session exists in memory
        if upload_id in self.sessions:
            return self.sessions[upload_id]
        
        # Try to reconstruct from storage
        received_chunks = self.storage.list_chunks(upload_id)
        if not received_chunks:
            return None
        
        # We can't fully reconstruct without metadata, but we can create a partial session
        # In a production system, you'd store session metadata in a database
        # For now, we'll return None and let the client re-init if needed
        return None
    
    def upload_chunk(
        self, 
        upload_id: str, 
        chunk_index: int, 
        chunk_data: bytes,
        total_chunks: int
    ) -> tuple[bool, int, str]:
        """
        Upload a chunk with idempotency.
        
        Args:
            upload_id: Upload session identifier
            chunk_index: Zero-based chunk index
            chunk_data: Binary chunk data
            total_chunks: Total number of chunks (for validation)
            
        Returns:
            Tuple of (success, received_chunks_count, message)
        """
        # Get or create session
        session = self.get_session(upload_id)
        if session is None:
            # Try to reconstruct from storage
            session = self.get_or_create_session_from_storage(upload_id)
            if session is None:
                return False, 0, f"Upload session {upload_id} not found"
        
        # Validate chunk index
        if chunk_index < 0 or chunk_index >= session.total_chunks:
            return False, len(session.received_chunks), f"Invalid chunk index: {chunk_index}"
        
        # Validate total chunks matches session
        if total_chunks != session.total_chunks:
            return False, len(session.received_chunks), f"Total chunks mismatch: expected {session.total_chunks}, got {total_chunks}"
        
        # Idempotency check: if chunk already exists and matches size, skip
        if self.storage.chunk_exists(upload_id, chunk_index):
            existing_size = self.storage.get_chunk_size(upload_id, chunk_index)
            if existing_size == len(chunk_data):
                # Chunk already exists with correct size, mark as received
                if chunk_index not in session.received_chunks:
                    session.received_chunks.add(chunk_index)
                return True, len(session.received_chunks), "Chunk already uploaded (idempotent)"
        
        # Store chunk atomically
        success = self.storage.store_chunk(upload_id, chunk_index, chunk_data)
        if success:
            session.received_chunks.add(chunk_index)
            return True, len(session.received_chunks), "Chunk uploaded successfully"
        else:
            return False, len(session.received_chunks), "Failed to store chunk"
    
    def get_upload_status(self, upload_id: str) -> Optional[dict]:
        """
        Get the status of an upload session.
        
        Args:
            upload_id: Upload session identifier
            
        Returns:
            Dictionary with status information, or None if session not found
        """
        session = self.get_session(upload_id)
        if session is None:
            # Try to reconstruct from storage
            received_chunks = self.storage.list_chunks(upload_id)
            if not received_chunks:
                return None
            
            # Return partial status (we don't have full session info)
            # In production, store session metadata in database
            return {
                "upload_id": upload_id,
                "received_chunks": sorted(received_chunks),
                "is_complete": False,  # Can't determine without session metadata
                "total_chunks": None  # Unknown without session
            }
        
        return {
            "upload_id": upload_id,
            "total_chunks": session.total_chunks,
            "received_chunks": sorted(session.received_chunks),
            "is_complete": session.is_complete()
        }
    
    def complete_upload(self, upload_id: str) -> Optional[tuple[Path, FileMetadata]]:
        """
        Complete an upload by reassembling chunks.
        
        Args:
            upload_id: Upload session identifier
            
        Returns:
            Tuple of (file_path, metadata) if successful, None otherwise
        """
        session = self.get_session(upload_id)
        if session is None:
            return None
        
        # Verify all chunks are present
        if not session.is_complete():
            missing = session.get_missing_chunks()
            raise ValueError(f"Upload incomplete: missing chunks {missing}")
        
        # Reassemble file
        output_path = self.storage.reassemble_file(
            upload_id=upload_id,
            total_chunks=session.total_chunks,
            output_filename=session.filename,
            expected_size=session.total_size
        )
        
        if output_path is None:
            return None
        
        # Generate metadata
        checksum = self.storage.get_file_checksum(output_path) if session.checksum else None
        file_type = self._detect_file_type(session.filename)
        
        metadata = FileMetadata(
            uploadId=upload_id,
            filename=session.filename,
            size=session.total_size,
            checksum=checksum,
            timestamp=datetime.now(timezone.utc).isoformat(),
            fileType=file_type,
            filepath=str(output_path)
        )
        
        # Cleanup temporary chunks
        self.storage.cleanup_chunks(upload_id)
        
        # Remove session from memory
        if upload_id in self.sessions:
            del self.sessions[upload_id]
        
        return output_path, metadata
    
    def _detect_file_type(self, filename: str) -> str:
        """Detect file type from extension."""
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        # AI-related file types
        dataset_extensions = {'jsonl', 'json', 'csv', 'parquet', 'tsv', 'txt'}
        model_extensions = {'pt', 'pth', 'ckpt', 'safetensors', 'onnx', 'pb', 'h5'}
        archive_extensions = {'zip', 'tar', 'gz', 'bz2'}
        
        if ext in dataset_extensions:
            return 'dataset'
        elif ext in model_extensions:
            return 'model_artifact'
        elif ext in archive_extensions:
            return 'archive'
        else:
            return 'unknown'

