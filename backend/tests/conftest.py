"""
Pytest configuration and shared fixtures.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator

from app.storage import Storage
from app.upload_service import UploadService
from app.ai_integration import AIIntegration
from app.models import InitUploadRequest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def storage(temp_dir: Path) -> Storage:
    """Create a Storage instance with temporary directories."""
    uploads_dir = temp_dir / "uploads"
    completed_dir = temp_dir / "completed"
    return Storage(uploads_dir=str(uploads_dir), completed_dir=str(completed_dir))


@pytest.fixture
def upload_service(storage: Storage) -> UploadService:
    """Create an UploadService instance."""
    return UploadService(storage=storage, chunk_size=1024 * 1024)  # 1MB chunks


@pytest.fixture
def ai_integration(temp_dir: Path) -> AIIntegration:
    """Create an AIIntegration instance with temporary metadata store."""
    metadata_store = temp_dir / "metadata_store.json"
    return AIIntegration(metadata_store_path=str(metadata_store))


@pytest.fixture
def sample_file_data() -> bytes:
    """Generate sample file data for testing."""
    return b"x" * (5 * 1024 * 1024)  # 5MB of data


@pytest.fixture
def sample_chunk_data() -> bytes:
    """Generate sample chunk data (1MB)."""
    return b"x" * (1024 * 1024)


@pytest.fixture
def init_upload_request() -> InitUploadRequest:
    """Create a sample init upload request."""
    return InitUploadRequest(
        filename="test_file.jsonl",
        totalSize=5 * 1024 * 1024,  # 5MB
        checksum=None
    )


@pytest.fixture
def large_file_data() -> bytes:
    """Generate large file data for stress testing (100MB)."""
    return b"y" * (100 * 1024 * 1024)


@pytest.fixture
def many_chunks_data() -> bytes:
    """Generate data that will create many chunks (50MB = 50 chunks)."""
    return b"z" * (50 * 1024 * 1024)


# Note: benchmark fixture is provided by pytest-benchmark if installed
# Tests will handle None gracefully
