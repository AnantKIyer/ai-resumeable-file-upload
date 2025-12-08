"""
Unit tests for upload_service module.
"""
import pytest
from app.upload_service import UploadService, UploadSession
from app.models import InitUploadRequest


@pytest.mark.unit
class TestUploadSession:
    """Test UploadSession dataclass."""
    
    def test_upload_session_creation(self):
        """Test creating an upload session."""
        session = UploadSession(
            upload_id="test-123",
            filename="test.jsonl",
            total_size=1024 * 1024 * 5,
            total_chunks=5,
            chunk_size=1024 * 1024
        )
        
        assert session.upload_id == "test-123"
        assert session.filename == "test.jsonl"
        assert session.total_chunks == 5
    
    def test_is_complete(self):
        """Test checking if upload is complete."""
        session = UploadSession(
            upload_id="test",
            filename="test.jsonl",
            total_size=1024 * 1024 * 3,
            total_chunks=3,
            chunk_size=1024 * 1024
        )
        
        assert session.is_complete() is False
        
        session.received_chunks = {0, 1, 2}
        assert session.is_complete() is True
    
    def test_get_missing_chunks(self):
        """Test getting missing chunks."""
        session = UploadSession(
            upload_id="test",
            filename="test.jsonl",
            total_size=1024 * 1024 * 5,
            total_chunks=5,
            chunk_size=1024 * 1024
        )
        
        session.received_chunks = {0, 2, 4}
        missing = session.get_missing_chunks()
        assert missing == [1, 3]


@pytest.mark.unit
class TestUploadService:
    """Test UploadService class."""
    
    def test_init_upload(self, upload_service: UploadService, init_upload_request: InitUploadRequest):
        """Test initializing an upload."""
        upload_id, chunk_size = upload_service.init_upload(init_upload_request)
        
        assert upload_id is not None
        assert len(upload_id) > 0
        assert chunk_size == 1024 * 1024  # 1MB
        
        # Verify session exists
        session = upload_service.get_session(upload_id)
        assert session is not None
        assert session.filename == init_upload_request.filename
        assert session.total_size == init_upload_request.totalSize
    
    def test_get_session(self, upload_service: UploadService, init_upload_request: InitUploadRequest):
        """Test getting a session."""
        upload_id, _ = upload_service.init_upload(init_upload_request)
        
        session = upload_service.get_session(upload_id)
        assert session is not None
        assert session.upload_id == upload_id
    
    def test_get_session_nonexistent(self, upload_service: UploadService):
        """Test getting non-existent session returns None."""
        session = upload_service.get_session("nonexistent-id")
        assert session is None
    
    def test_upload_chunk(self, upload_service: UploadService, init_upload_request: InitUploadRequest):
        """Test uploading a chunk."""
        upload_id, _ = upload_service.init_upload(init_upload_request)
        chunk_data = b"x" * (1024 * 1024)
        
        success, received_count, message = upload_service.upload_chunk(
            upload_id, 0, chunk_data, 5
        )
        
        assert success is True
        assert received_count == 1
        assert "success" in message.lower()
        
        # Verify chunk was stored
        session = upload_service.get_session(upload_id)
        assert 0 in session.received_chunks
    
    def test_upload_chunk_idempotent(self, upload_service: UploadService, init_upload_request: InitUploadRequest):
        """Test uploading the same chunk twice is idempotent."""
        upload_id, _ = upload_service.init_upload(init_upload_request)
        chunk_data = b"idempotent chunk"
        
        # Upload twice
        success1, count1, _ = upload_service.upload_chunk(upload_id, 0, chunk_data, 5)
        success2, count2, _ = upload_service.upload_chunk(upload_id, 0, chunk_data, 5)
        
        assert success1 is True
        assert success2 is True
        assert count1 == count2 == 1  # Should only count once
    
    def test_upload_chunk_invalid_index(self, upload_service: UploadService, init_upload_request: InitUploadRequest):
        """Test uploading chunk with invalid index fails."""
        upload_id, _ = upload_service.init_upload(init_upload_request)
        chunk_data = b"test"
        
        # Try invalid index
        success, _, message = upload_service.upload_chunk(upload_id, 999, chunk_data, 5)
        assert success is False
        assert "invalid" in message.lower()
    
    def test_upload_chunk_total_mismatch(self, upload_service: UploadService, init_upload_request: InitUploadRequest):
        """Test uploading chunk with mismatched total chunks fails."""
        upload_id, _ = upload_service.init_upload(init_upload_request)
        chunk_data = b"test"
        
        # Try with wrong total chunks
        success, _, message = upload_service.upload_chunk(upload_id, 0, chunk_data, 10)
        assert success is False
        assert "mismatch" in message.lower()
    
    def test_get_upload_status(self, upload_service: UploadService, init_upload_request: InitUploadRequest):
        """Test getting upload status."""
        upload_id, _ = upload_service.init_upload(init_upload_request)
        
        # Upload some chunks
        for i in range(3):
            chunk_data = b"x" * (1024 * 1024)
            upload_service.upload_chunk(upload_id, i, chunk_data, 5)
        
        status = upload_service.get_upload_status(upload_id)
        assert status is not None
        assert status["upload_id"] == upload_id
        assert status["total_chunks"] == 5
        assert len(status["received_chunks"]) == 3
        assert status["is_complete"] is False
    
    def test_get_upload_status_complete(self, upload_service: UploadService, init_upload_request: InitUploadRequest):
        """Test getting status for complete upload."""
        upload_id, _ = upload_service.init_upload(init_upload_request)
        
        # Upload all chunks
        for i in range(5):
            chunk_data = b"x" * (1024 * 1024)
            upload_service.upload_chunk(upload_id, i, chunk_data, 5)
        
        status = upload_service.get_upload_status(upload_id)
        assert status["is_complete"] is True
        assert len(status["received_chunks"]) == 5
    
    def test_get_upload_status_nonexistent(self, upload_service: UploadService):
        """Test getting status for non-existent upload."""
        status = upload_service.get_upload_status("nonexistent-id")
        assert status is None
    
    def test_complete_upload(self, upload_service: UploadService, init_upload_request: InitUploadRequest):
        """Test completing an upload."""
        upload_id, _ = upload_service.init_upload(init_upload_request)
        
        # Upload all chunks
        chunk_data = b"x" * (1024 * 1024)
        for i in range(5):
            upload_service.upload_chunk(upload_id, i, chunk_data, 5)
        
        # Complete upload
        result = upload_service.complete_upload(upload_id)
        assert result is not None
        
        file_path, metadata = result
        assert file_path.exists()
        assert metadata.filename == init_upload_request.filename
    
    def test_complete_upload_incomplete(self, upload_service: UploadService, init_upload_request: InitUploadRequest):
        """Test completing incomplete upload fails."""
        upload_id, _ = upload_service.init_upload(init_upload_request)
        
        # Upload only some chunks
        chunk_data = b"x" * (1024 * 1024)
        upload_service.upload_chunk(upload_id, 0, chunk_data, 5)
        upload_service.upload_chunk(upload_id, 2, chunk_data, 5)
        
        # Try to complete
        with pytest.raises(ValueError, match="incomplete"):
            upload_service.complete_upload(upload_id)
    
    def test_complete_upload_nonexistent(self, upload_service: UploadService):
        """Test completing non-existent upload returns None."""
        result = upload_service.complete_upload("nonexistent-id")
        assert result is None
    
    def test_detect_file_type(self, upload_service: UploadService):
        """Test file type detection."""
        assert upload_service._detect_file_type("data.jsonl") == "dataset"
        assert upload_service._detect_file_type("model.pt") == "model_artifact"
        assert upload_service._detect_file_type("archive.zip") == "archive"
        assert upload_service._detect_file_type("unknown.xyz") == "unknown"
