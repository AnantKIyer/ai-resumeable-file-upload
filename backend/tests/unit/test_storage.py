"""
Unit tests for storage module.
"""
import pytest
from pathlib import Path

from app.storage import Storage


@pytest.mark.unit
class TestStorage:
    """Test Storage class."""
    
    def test_storage_initialization(self, storage: Storage, temp_dir: Path):
        """Test storage initialization creates directories."""
        assert storage.uploads_dir.exists()
        assert storage.completed_dir.exists()
    
    def test_store_chunk(self, storage: Storage):
        """Test storing a chunk."""
        upload_id = "test-upload-123"
        chunk_index = 0
        chunk_data = b"test chunk data"
        
        result = storage.store_chunk(upload_id, chunk_index, chunk_data)
        assert result is True
        
        chunk_path = storage.get_chunk_path(upload_id, chunk_index)
        assert chunk_path.exists()
        assert chunk_path.read_bytes() == chunk_data
    
    def test_store_chunk_atomic(self, storage: Storage):
        """Test that chunk storage is atomic."""
        upload_id = "test-upload-atomic"
        chunk_index = 0
        chunk_data = b"atomic test data"
        
        storage.store_chunk(upload_id, chunk_index, chunk_data)
        
        # Verify chunk exists and is complete
        chunk_path = storage.get_chunk_path(upload_id, chunk_index)
        assert chunk_path.exists()
        assert not chunk_path.with_suffix('.chunk.tmp').exists()  # Temp file should be gone
    
    def test_chunk_exists(self, storage: Storage):
        """Test checking if chunk exists."""
        upload_id = "test-upload-exists"
        chunk_index = 0
        
        assert storage.chunk_exists(upload_id, chunk_index) is False
        
        storage.store_chunk(upload_id, chunk_index, b"data")
        assert storage.chunk_exists(upload_id, chunk_index) is True
    
    def test_get_chunk(self, storage: Storage):
        """Test retrieving a chunk."""
        upload_id = "test-upload-get"
        chunk_index = 0
        chunk_data = b"retrieved chunk data"
        
        storage.store_chunk(upload_id, chunk_index, chunk_data)
        
        retrieved = storage.get_chunk(upload_id, chunk_index)
        assert retrieved == chunk_data
    
    def test_get_chunk_nonexistent(self, storage: Storage):
        """Test retrieving non-existent chunk returns None."""
        upload_id = "test-upload-nonexistent"
        chunk_index = 999
        
        retrieved = storage.get_chunk(upload_id, chunk_index)
        assert retrieved is None
    
    def test_get_chunk_size(self, storage: Storage):
        """Test getting chunk size."""
        upload_id = "test-upload-size"
        chunk_index = 0
        chunk_data = b"x" * 1000
        
        storage.store_chunk(upload_id, chunk_index, chunk_data)
        
        size = storage.get_chunk_size(upload_id, chunk_index)
        assert size == 1000
    
    def test_list_chunks(self, storage: Storage):
        """Test listing chunks for an upload."""
        upload_id = "test-upload-list"
        
        # Store multiple chunks
        for i in range(5):
            storage.store_chunk(upload_id, i, f"chunk-{i}".encode())
        
        chunks = storage.list_chunks(upload_id)
        assert chunks == [0, 1, 2, 3, 4]
    
    def test_list_chunks_empty(self, storage: Storage):
        """Test listing chunks for upload with no chunks."""
        upload_id = "test-upload-empty"
        
        chunks = storage.list_chunks(upload_id)
        assert chunks == []
    
    def test_list_chunks_out_of_order(self, storage: Storage):
        """Test listing chunks returns sorted indices."""
        upload_id = "test-upload-out-of-order"
        
        # Store chunks out of order
        storage.store_chunk(upload_id, 3, b"chunk-3")
        storage.store_chunk(upload_id, 1, b"chunk-1")
        storage.store_chunk(upload_id, 5, b"chunk-5")
        storage.store_chunk(upload_id, 2, b"chunk-2")
        
        chunks = storage.list_chunks(upload_id)
        assert chunks == [1, 2, 3, 5]
    
    def test_reassemble_file(self, storage: Storage, sample_file_data: bytes):
        """Test reassembling file from chunks."""
        upload_id = "test-upload-reassemble"
        chunk_size = 1024 * 1024  # 1MB
        total_chunks = (len(sample_file_data) + chunk_size - 1) // chunk_size
        
        # Store chunks
        for i in range(total_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, len(sample_file_data))
            chunk_data = sample_file_data[start:end]
            storage.store_chunk(upload_id, i, chunk_data)
        
        # Reassemble
        output_path = storage.reassemble_file(
            upload_id, total_chunks, "reassembled.bin", len(sample_file_data)
        )
        
        assert output_path is not None
        assert output_path.exists()
        assert output_path.read_bytes() == sample_file_data
    
    def test_reassemble_file_missing_chunks(self, storage: Storage):
        """Test reassembling file with missing chunks fails."""
        upload_id = "test-upload-missing"
        
        # Store only some chunks
        storage.store_chunk(upload_id, 0, b"chunk-0")
        storage.store_chunk(upload_id, 2, b"chunk-2")
        # Missing chunk 1
        
        output_path = storage.reassemble_file(upload_id, 3, "missing.bin")
        assert output_path is None
    
    def test_reassemble_file_size_mismatch(self, storage: Storage):
        """Test reassembling file with size mismatch fails."""
        upload_id = "test-upload-size-mismatch"
        
        # Store chunks
        storage.store_chunk(upload_id, 0, b"x" * 1000)
        storage.store_chunk(upload_id, 1, b"y" * 1000)
        
        # Try to reassemble with wrong expected size
        output_path = storage.reassemble_file(
            upload_id, 2, "mismatch.bin", expected_size=5000
        )
        
        assert output_path is None
    
    def test_cleanup_chunks(self, storage: Storage):
        """Test cleaning up chunks."""
        upload_id = "test-upload-cleanup"
        
        # Store chunks
        for i in range(3):
            storage.store_chunk(upload_id, i, f"chunk-{i}".encode())
        
        # Verify chunks exist
        assert len(storage.list_chunks(upload_id)) == 3
        
        # Cleanup
        result = storage.cleanup_chunks(upload_id)
        assert result is True
        
        # Verify chunks are gone
        assert storage.list_chunks(upload_id) == []
    
    def test_get_file_checksum(self, storage: Storage, temp_dir: Path):
        """Test calculating file checksum."""
        test_file = temp_dir / "test_checksum.txt"
        test_file.write_text("test content")
        
        checksum = storage.get_file_checksum(test_file)
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 hex digest length
    
    def test_store_chunk_idempotent(self, storage: Storage):
        """Test that storing the same chunk twice is idempotent."""
        upload_id = "test-upload-idempotent"
        chunk_index = 0
        chunk_data = b"idempotent data"
        
        # Store twice
        result1 = storage.store_chunk(upload_id, chunk_index, chunk_data)
        result2 = storage.store_chunk(upload_id, chunk_index, chunk_data)
        
        assert result1 is True
        assert result2 is True
        
        # Verify data is correct
        retrieved = storage.get_chunk(upload_id, chunk_index)
        assert retrieved == chunk_data
