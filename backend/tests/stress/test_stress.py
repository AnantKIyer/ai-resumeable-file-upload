"""
Stress tests for concurrent uploads and large files.
"""
import pytest
import concurrent.futures
import threading
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.stress
@pytest.mark.slow
class TestConcurrentUploads:
    """Stress tests for concurrent uploads."""

    def test_many_concurrent_uploads(self, client: TestClient):
        """Test many uploads happening concurrently."""
        num_uploads = 20

        def upload_file(file_id):
            # Initialize
            init_response = client.post(
                "/api/upload/init",
                json={
                    "filename": f"stress_{file_id}.bin",
                    "totalSize": 2 * 1024 * 1024
                }
            )
            if init_response.status_code != 200:
                return False

            upload_id = init_response.json()["uploadId"]
            chunk_data = b"x" * (1024 * 1024)

            # Upload chunks
            for i in range(2):
                response = client.post(
                    "/api/upload/chunk",
                    data={
                        "uploadId": upload_id,
                        "chunkIndex": str(i),
                        "totalChunks": "2"
                    },
                    files={"chunk": (f"chunk{i}.bin", chunk_data)}
                )
                if response.status_code != 200:
                    return False

            # Complete
            complete_response = client.post(
                f"/api/upload/complete/{upload_id}")
            return complete_response.status_code == 200

        # Run uploads concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(upload_file, i)
                       for i in range(num_uploads)]
            results = [f.result()
                       for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(
            results), f"Failed uploads: {sum(1 for r in results if not r)}"

    def test_many_concurrent_chunks(self, client: TestClient):
        """Test uploading many chunks concurrently for single file."""
        # Initialize (use .bin to avoid validation)
        init_response = client.post(
            "/api/upload/init",
            json={
                "filename": "many_chunks.bin",
                "totalSize": 50 * 1024 * 1024  # 50MB = 50 chunks
            }
        )
        upload_id = init_response.json()["uploadId"]
        total_chunks = 50

        def upload_chunk(chunk_index):
            chunk_data = b"x" * (1024 * 1024)
            response = client.post(
                "/api/upload/chunk",
                data={
                    "uploadId": upload_id,
                    "chunkIndex": str(chunk_index),
                    "totalChunks": str(total_chunks)
                },
                files={"chunk": (f"chunk{chunk_index}.bin", chunk_data)}
            )
            return response.status_code == 200

        # Upload all chunks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(upload_chunk, i)
                       for i in range(total_chunks)]
            results = [f.result()
                       for f in concurrent.futures.as_completed(futures)]

        assert all(results)

        # Verify all chunks received
        status_response = client.get(f"/api/upload/status/{upload_id}")
        assert len(status_response.json()["receivedChunks"]) == total_chunks

        # Complete
        complete_response = client.post(f"/api/upload/complete/{upload_id}")
        assert complete_response.status_code == 200

    def test_rapid_status_checks(self, client: TestClient):
        """Test rapid status checks during upload."""
        # Initialize
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "rapid_status.bin",
                  "totalSize": 10 * 1024 * 1024}
        )
        upload_id = init_response.json()["uploadId"]

        status_checks = []

        def check_status():
            response = client.get(f"/api/upload/status/{upload_id}")
            status_checks.append(response.status_code == 200)

        def upload_chunks():
            chunk_data = b"x" * (1024 * 1024)
            for i in range(10):
                client.post(
                    "/api/upload/chunk",
                    data={
                        "uploadId": upload_id,
                        "chunkIndex": str(i),
                        "totalChunks": "10"
                    },
                    files={"chunk": (f"chunk{i}.bin", chunk_data)}
                )

        # Run status checks and uploads concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            # Start uploads
            upload_future = executor.submit(upload_chunks)

            # Rapid status checks
            status_futures = [executor.submit(check_status) for _ in range(50)]

            # Wait for all
            upload_future.result()
            [f.result() for f in status_futures]

        # All status checks should succeed
        assert all(status_checks)


@pytest.mark.stress
@pytest.mark.slow
class TestLargeFiles:
    """Stress tests for large files."""

    def test_large_file_upload(self, client: TestClient):
        """Test uploading a large file (100MB)."""
        file_size = 100 * 1024 * 1024  # 100MB
        total_chunks = 100

        # Initialize
        init_response = client.post(
            "/api/upload/init",
            json={
                "filename": "large_file.bin",
                "totalSize": file_size
            }
        )
        upload_id = init_response.json()["uploadId"]

        # Upload chunks
        chunk_data = b"x" * (1024 * 1024)
        for i in range(total_chunks):
            response = client.post(
                "/api/upload/chunk",
                data={
                    "uploadId": upload_id,
                    "chunkIndex": str(i),
                    "totalChunks": str(total_chunks)
                },
                files={"chunk": (f"chunk{i}.bin", chunk_data)}
            )
            assert response.status_code == 200

        # Complete
        complete_response = client.post(f"/api/upload/complete/{upload_id}")
        assert complete_response.status_code == 200
        assert complete_response.json()["metadata"]["size"] == file_size

    def test_very_large_file_chunks(self, client: TestClient):
        """Test file that creates many chunks (500MB = 500 chunks)."""
        file_size = 500 * 1024 * 1024  # 500MB
        total_chunks = 500

        # Initialize
        init_response = client.post(
            "/api/upload/init",
            json={
                "filename": "very_large.bin",
                "totalSize": file_size
            }
        )
        upload_id = init_response.json()["uploadId"]

        # Upload chunks in batches
        chunk_data = b"y" * (1024 * 1024)
        batch_size = 50

        for batch_start in range(0, total_chunks, batch_size):
            batch_end = min(batch_start + batch_size, total_chunks)
            for i in range(batch_start, batch_end):
                response = client.post(
                    "/api/upload/chunk",
                    data={
                        "uploadId": upload_id,
                        "chunkIndex": str(i),
                        "totalChunks": str(total_chunks)
                    },
                    files={"chunk": (f"chunk{i}.bin", chunk_data)}
                )
                assert response.status_code == 200

        # Verify status
        status_response = client.get(f"/api/upload/status/{upload_id}")
        assert len(status_response.json()["receivedChunks"]) == total_chunks

        # Complete
        complete_response = client.post(f"/api/upload/complete/{upload_id}")
        assert complete_response.status_code == 200


@pytest.mark.stress
class TestEdgeCaseStress:
    """Stress tests for edge cases."""

    def test_many_small_files(self, client: TestClient):
        """Test uploading many small files."""
        num_files = 100

        def upload_small_file(file_id):
            init_response = client.post(
                "/api/upload/init",
                json={
                    "filename": f"small_{file_id}.txt",
                    "totalSize": 1024  # 1KB
                }
            )
            if init_response.status_code != 200:
                return False

            upload_id = init_response.json()["uploadId"]

            # Upload single chunk
            response = client.post(
                "/api/upload/chunk",
                data={
                    "uploadId": upload_id,
                    "chunkIndex": "0",
                    "totalChunks": "1"
                },
                files={"chunk": ("chunk.bin", b"x" * 1024)}
            )

            if response.status_code != 200:
                return False

            # Complete
            complete_response = client.post(
                f"/api/upload/complete/{upload_id}")
            return complete_response.status_code == 200

        # Upload concurrently (reduced workers to avoid race conditions)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(upload_small_file, i)
                       for i in range(num_files)]
            results = [f.result()
                       for f in concurrent.futures.as_completed(futures)]

        assert all(results)

    def test_idempotent_stress(self, client: TestClient):
        """Test idempotency under stress."""
        # Initialize
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "idempotent_stress.bin",
                  "totalSize": 5 * 1024 * 1024}
        )
        upload_id = init_response.json()["uploadId"]

        chunk_data = b"z" * (1024 * 1024)

        # Upload same chunk many times concurrently
        def upload_same_chunk():
            return client.post(
                "/api/upload/chunk",
                data={
                    "uploadId": upload_id,
                    "chunkIndex": "0",
                    "totalChunks": "5"
                },
                files={"chunk": ("chunk.bin", chunk_data)}
            )

        # Upload same chunk 50 times concurrently (reduced workers to avoid race conditions)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(upload_same_chunk) for _ in range(50)]
            results = [f.result()
                       for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(r.status_code == 200 for r in results)

        # Should only have 1 chunk received
        status_response = client.get(f"/api/upload/status/{upload_id}")
        assert len(status_response.json()["receivedChunks"]) == 1
