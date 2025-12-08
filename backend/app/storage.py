"""
Filesystem storage abstraction for chunk storage and file reassembly.
"""
import os
import shutil
from pathlib import Path
from typing import Optional
import hashlib


class Storage:
    """Handles filesystem operations for chunk storage and file reassembly."""

    def __init__(self, uploads_dir: str = None, completed_dir: str = None):
        """
        Initialize storage with directory paths.

        Args:
            uploads_dir: Directory for temporary chunk storage
            completed_dir: Directory for completed file storage
        """
        # Default to backend directory
        backend_dir = Path(__file__).parent.parent
        if uploads_dir is None:
            uploads_dir = backend_dir / "uploads"
        if completed_dir is None:
            completed_dir = backend_dir / "completed"

        self.uploads_dir = Path(uploads_dir)
        self.completed_dir = Path(completed_dir)

        # Create directories if they don't exist
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.completed_dir.mkdir(parents=True, exist_ok=True)

    def get_chunk_path(self, upload_id: str, chunk_index: int) -> Path:
        """Get the filesystem path for a specific chunk."""
        upload_dir = self.uploads_dir / upload_id
        # Use exist_ok=True to handle race conditions in concurrent scenarios
        try:
            upload_dir.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            # Directory was created by another thread, that's fine
            pass
        return upload_dir / f"{chunk_index}.chunk"

    def store_chunk(self, upload_id: str, chunk_index: int, data: bytes) -> bool:
        """
        Store a chunk atomically.

        Args:
            upload_id: Unique upload session identifier
            chunk_index: Zero-based chunk index
            data: Binary chunk data

        Returns:
            True if chunk was stored successfully, False otherwise
        """
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Ensure upload directory exists (handle race conditions)
                upload_dir = self.uploads_dir / upload_id
                try:
                    upload_dir.mkdir(parents=True, exist_ok=True)
                except (FileExistsError, OSError):
                    # Directory was created by another thread, that's fine
                    pass

                chunk_path = upload_dir / f"{chunk_index}.chunk"

                # Atomic write: write to temp file first, then rename
                temp_path = chunk_path.with_suffix('.chunk.tmp')

                # Ensure directory exists before writing
                if not upload_dir.exists():
                    upload_dir.mkdir(parents=True, exist_ok=True)

                with open(temp_path, 'wb') as f:
                    f.write(data)

                # Ensure directory still exists before rename (handle race conditions)
                if not upload_dir.exists():
                    upload_dir.mkdir(parents=True, exist_ok=True)

                # Atomic rename (works on most filesystems)
                temp_path.replace(chunk_path)
                return True
            except (FileNotFoundError, OSError) as e:
                if attempt < max_retries - 1:
                    # Retry after a short delay
                    time.sleep(0.01 * (attempt + 1))
                    continue
                print(
                    f"Error storing chunk {chunk_index} for upload {upload_id} after {max_retries} attempts: {e}")
                return False
            except Exception as e:
                print(
                    f"Error storing chunk {chunk_index} for upload {upload_id}: {e}")
                return False
        return False

    def chunk_exists(self, upload_id: str, chunk_index: int) -> bool:
        """Check if a chunk file exists."""
        chunk_path = self.get_chunk_path(upload_id, chunk_index)
        return chunk_path.exists()

    def get_chunk(self, upload_id: str, chunk_index: int) -> Optional[bytes]:
        """
        Read a chunk from storage.

        Args:
            upload_id: Unique upload session identifier
            chunk_index: Zero-based chunk index

        Returns:
            Chunk data as bytes, or None if chunk doesn't exist
        """
        chunk_path = self.get_chunk_path(upload_id, chunk_index)
        if not chunk_path.exists():
            return None

        try:
            with open(chunk_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(
                f"Error reading chunk {chunk_index} for upload {upload_id}: {e}")
            return None

    def get_chunk_size(self, upload_id: str, chunk_index: int) -> Optional[int]:
        """Get the size of a stored chunk."""
        chunk_path = self.get_chunk_path(upload_id, chunk_index)
        if not chunk_path.exists():
            return None
        return chunk_path.stat().st_size

    def list_chunks(self, upload_id: str) -> list[int]:
        """
        List all chunk indices that have been stored for an upload.

        Args:
            upload_id: Unique upload session identifier

        Returns:
            Sorted list of chunk indices
        """
        upload_dir = self.uploads_dir / upload_id
        if not upload_dir.exists():
            return []

        chunks = []
        for chunk_file in upload_dir.glob("*.chunk"):
            try:
                chunk_index = int(chunk_file.stem)
                chunks.append(chunk_index)
            except ValueError:
                continue

        return sorted(chunks)

    def reassemble_file(
        self,
        upload_id: str,
        total_chunks: int,
        output_filename: str,
        expected_size: Optional[int] = None
    ) -> Optional[Path]:
        """
        Reassemble chunks into the final file.

        Args:
            upload_id: Unique upload session identifier
            total_chunks: Total number of chunks expected
            output_filename: Name for the output file
            expected_size: Optional expected file size for validation

        Returns:
            Path to the reassembled file, or None if reassembly failed
        """
        output_path = self.completed_dir / output_filename

        try:
            # Verify all chunks exist
            received_chunks = self.list_chunks(upload_id)
            expected_indices = set(range(total_chunks))
            received_indices = set(received_chunks)

            if expected_indices != received_indices:
                missing = expected_indices - received_indices
                raise ValueError(f"Missing chunks: {sorted(missing)}")

            # Reassemble chunks in order
            with open(output_path, 'wb') as outfile:
                for chunk_index in range(total_chunks):
                    chunk_data = self.get_chunk(upload_id, chunk_index)
                    if chunk_data is None:
                        raise ValueError(
                            f"Chunk {chunk_index} not found during reassembly")
                    outfile.write(chunk_data)

            # Validate size if provided
            if expected_size is not None:
                actual_size = output_path.stat().st_size
                if actual_size != expected_size:
                    output_path.unlink()  # Remove incomplete file
                    raise ValueError(
                        f"Size mismatch: expected {expected_size} bytes, got {actual_size} bytes"
                    )

            return output_path
        except Exception as e:
            print(f"Error reassembling file for upload {upload_id}: {e}")
            if output_path.exists():
                output_path.unlink()
            return None

    def cleanup_chunks(self, upload_id: str) -> bool:
        """
        Remove all temporary chunks for an upload session.

        Args:
            upload_id: Unique upload session identifier

        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            upload_dir = self.uploads_dir / upload_id
            if upload_dir.exists():
                shutil.rmtree(upload_dir)
            return True
        except Exception as e:
            print(f"Error cleaning up chunks for upload {upload_id}: {e}")
            return False

    def get_file_checksum(self, filepath: Path) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
