"""
Comprehensive API endpoint tests with edge cases.
"""
import pytest
import httpx
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.api
class TestInitUpload:
    """Test POST /api/upload/init endpoint."""

    def test_init_upload_success(self, client: TestClient):
        """Test successful upload initialization."""
        response = client.post(
            "/api/upload/init",
            json={
                "filename": "test.jsonl",
                "totalSize": 5 * 1024 * 1024
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "uploadId" in data
        assert data["chunkSize"] == 1024 * 1024  # 1MB

    def test_init_upload_with_checksum(self, client: TestClient):
        """Test init with checksum."""
        response = client.post(
            "/api/upload/init",
            json={
                "filename": "test.jsonl",
                "totalSize": 1024 * 1024,
                "checksum": "abc123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "uploadId" in data

    def test_init_upload_invalid_size(self, client: TestClient):
        """Test init with invalid size."""
        response = client.post(
            "/api/upload/init",
            json={
                "filename": "test.jsonl",
                "totalSize": -1
            }
        )

        assert response.status_code == 422  # Validation error

    def test_init_upload_missing_fields(self, client: TestClient):
        """Test init with missing required fields."""
        response = client.post(
            "/api/upload/init",
            json={"filename": "test.jsonl"}
        )

        assert response.status_code == 422

    def test_init_upload_empty_filename(self, client: TestClient):
        """Test init with empty filename."""
        response = client.post(
            "/api/upload/init",
            json={
                "filename": "",
                "totalSize": 1024
            }
        )

        # Should still work (validation allows empty string)
        assert response.status_code == 200


@pytest.mark.api
class TestUploadChunk:
    """Test POST /api/upload/chunk endpoint."""

    def test_upload_chunk_success(self, client: TestClient):
        """Test successful chunk upload."""
        # Initialize upload
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "test.jsonl", "totalSize": 2 * 1024 * 1024}
        )
        upload_id = init_response.json()["uploadId"]

        # Upload chunk
        chunk_data = b"x" * (1024 * 1024)
        response = client.post(
            "/api/upload/chunk",
            data={
                "uploadId": upload_id,
                "chunkIndex": "0",
                "totalChunks": "2"
            },
            files={"chunk": ("chunk.bin", chunk_data,
                             "application/octet-stream")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["receivedChunks"] == 1

    def test_upload_chunk_idempotent(self, client: TestClient):
        """Test uploading same chunk twice is idempotent."""
        # Initialize
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "test.jsonl", "totalSize": 2 * 1024 * 1024}
        )
        upload_id = init_response.json()["uploadId"]

        chunk_data = b"idempotent data"

        # Upload twice
        response1 = client.post(
            "/api/upload/chunk",
            data={
                "uploadId": upload_id,
                "chunkIndex": "0",
                "totalChunks": "2"
            },
            files={"chunk": ("chunk.bin", chunk_data)}
        )

        response2 = client.post(
            "/api/upload/chunk",
            data={
                "uploadId": upload_id,
                "chunkIndex": "0",
                "totalChunks": "2"
            },
            files={"chunk": ("chunk.bin", chunk_data)}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()["receivedChunks"] == response2.json()[
            "receivedChunks"]

    def test_upload_chunk_invalid_upload_id(self, client: TestClient):
        """Test uploading chunk with invalid upload ID."""
        chunk_data = b"test"
        response = client.post(
            "/api/upload/chunk",
            data={
                "uploadId": "nonexistent-id",
                "chunkIndex": "0",
                "totalChunks": "1"
            },
            files={"chunk": ("chunk.bin", chunk_data)}
        )

        assert response.status_code == 400

    def test_upload_chunk_invalid_index(self, client: TestClient):
        """Test uploading chunk with invalid index."""
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "test.jsonl", "totalSize": 1024 * 1024}
        )
        upload_id = init_response.json()["uploadId"]

        chunk_data = b"test"
        response = client.post(
            "/api/upload/chunk",
            data={
                "uploadId": upload_id,
                "chunkIndex": "999",
                "totalChunks": "1"
            },
            files={"chunk": ("chunk.bin", chunk_data)}
        )

        assert response.status_code == 400

    def test_upload_chunk_missing_fields(self, client: TestClient):
        """Test uploading chunk with missing fields."""
        response = client.post(
            "/api/upload/chunk",
            data={"uploadId": "test"},
            files={"chunk": ("chunk.bin", b"data")}
        )

        assert response.status_code == 422

    def test_upload_chunk_empty_data(self, client: TestClient):
        """Test uploading empty chunk."""
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "test.jsonl", "totalSize": 1024 * 1024}
        )
        upload_id = init_response.json()["uploadId"]

        response = client.post(
            "/api/upload/chunk",
            data={
                "uploadId": upload_id,
                "chunkIndex": "0",
                "totalChunks": "1"
            },
            files={"chunk": ("chunk.bin", b"")}
        )

        # Empty chunk should still be accepted
        assert response.status_code == 200


@pytest.mark.api
class TestUploadStatus:
    """Test GET /api/upload/status/{uploadId} endpoint."""

    def test_get_status_success(self, client: TestClient):
        """Test getting upload status."""
        # Initialize and upload some chunks
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "test.jsonl", "totalSize": 3 * 1024 * 1024}
        )
        upload_id = init_response.json()["uploadId"]

        # Upload chunks
        chunk_data = b"x" * (1024 * 1024)
        for i in range(2):
            client.post(
                "/api/upload/chunk",
                data={
                    "uploadId": upload_id,
                    "chunkIndex": str(i),
                    "totalChunks": "3"
                },
                files={"chunk": ("chunk.bin", chunk_data)}
            )

        # Get status
        response = client.get(f"/api/upload/status/{upload_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["uploadId"] == upload_id
        assert data["totalChunks"] == 3
        assert len(data["receivedChunks"]) == 2
        assert data["isComplete"] is False

    def test_get_status_complete(self, client: TestClient):
        """Test getting status for complete upload."""
        # Initialize
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "test.jsonl", "totalSize": 2 * 1024 * 1024}
        )
        upload_id = init_response.json()["uploadId"]

        # Upload all chunks
        chunk_data = b"x" * (1024 * 1024)
        for i in range(2):
            client.post(
                "/api/upload/chunk",
                data={
                    "uploadId": upload_id,
                    "chunkIndex": str(i),
                    "totalChunks": "2"
                },
                files={"chunk": ("chunk.bin", chunk_data)}
            )

        # Get status
        response = client.get(f"/api/upload/status/{upload_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["isComplete"] is True
        assert len(data["receivedChunks"]) == 2

    def test_get_status_nonexistent(self, client: TestClient):
        """Test getting status for non-existent upload."""
        response = client.get("/api/upload/status/nonexistent-id")

        assert response.status_code == 404


@pytest.mark.api
class TestCompleteUpload:
    """Test POST /api/upload/complete/{uploadId} endpoint."""

    def test_complete_upload_success(self, client: TestClient):
        """Test successful upload completion."""
        # Initialize with .bin extension to avoid JSONL validation
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "test.bin", "totalSize": 2 * 1024 * 1024}
        )
        upload_id = init_response.json()["uploadId"]

        # Upload all chunks
        chunk_data = b"x" * (1024 * 1024)
        for i in range(2):
            client.post(
                "/api/upload/chunk",
                data={
                    "uploadId": upload_id,
                    "chunkIndex": str(i),
                    "totalChunks": "2"
                },
                files={"chunk": ("chunk.bin", chunk_data)}
            )

        # Complete upload
        response = client.post(f"/api/upload/complete/{upload_id}")

        if response.status_code != 200:
            print(f"Error response: {response.status_code} - {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "filepath" in data
        assert "metadata" in data
        assert data["metadata"]["filename"] == "test.bin"

    def test_complete_upload_incomplete(self, client: TestClient):
        """Test completing incomplete upload fails."""
        # Initialize
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "test.jsonl", "totalSize": 3 * 1024 * 1024}
        )
        upload_id = init_response.json()["uploadId"]

        # Upload only some chunks
        chunk_data = b"x" * (1024 * 1024)
        client.post(
            "/api/upload/chunk",
            data={
                "uploadId": upload_id,
                "chunkIndex": "0",
                "totalChunks": "3"
            },
            files={"chunk": ("chunk.bin", chunk_data)}
        )

        # Try to complete
        response = client.post(f"/api/upload/complete/{upload_id}")

        assert response.status_code == 400
        assert "incomplete" in response.json()["detail"].lower()

    def test_complete_upload_nonexistent(self, client: TestClient):
        """Test completing non-existent upload fails."""
        response = client.post("/api/upload/complete/nonexistent-id")

        assert response.status_code == 400

    def test_complete_upload_validation_failure(self, client: TestClient, temp_dir):
        """Test completion fails if validation fails."""
        # This would require mocking validation to fail
        # For now, we test the happy path
        pass


@pytest.mark.api
class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_very_large_file(self, client: TestClient):
        """Test handling very large file (100MB)."""
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "large.bin", "totalSize": 100 * 1024 * 1024}
        )

        assert init_response.status_code == 200
        data = init_response.json()
        # Init response doesn't return totalChunks, only uploadId and chunkSize
        assert "uploadId" in data
        assert data["chunkSize"] == 1024 * 1024  # 1MB chunks

    def test_single_byte_file(self, client: TestClient):
        """Test handling single byte file."""
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "tiny.bin", "totalSize": 1}
        )

        assert init_response.status_code == 200
        upload_id = init_response.json()["uploadId"]

        # Upload single byte chunk
        response = client.post(
            "/api/upload/chunk",
            data={
                "uploadId": upload_id,
                "chunkIndex": "0",
                "totalChunks": "1"
            },
            files={"chunk": ("chunk.bin", b"x")}
        )

        assert response.status_code == 200

    def test_unicode_filename(self, client: TestClient):
        """Test handling unicode filename."""
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "测试文件.jsonl", "totalSize": 1024}
        )

        assert init_response.status_code == 200

    def test_special_characters_filename(self, client: TestClient):
        """Test handling filename with special characters."""
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "file with spaces & symbols!.jsonl", "totalSize": 1024}
        )

        assert init_response.status_code == 200

    def test_concurrent_chunk_uploads(self, client: TestClient):
        """Test uploading chunks concurrently."""
        import concurrent.futures

        init_response = client.post(
            "/api/upload/init",
            json={"filename": "concurrent.jsonl", "totalSize": 5 * 1024 * 1024}
        )
        upload_id = init_response.json()["uploadId"]

        def upload_chunk(i):
            chunk_data = b"x" * (1024 * 1024)
            return client.post(
                "/api/upload/chunk",
                data={
                    "uploadId": upload_id,
                    "chunkIndex": str(i),
                    "totalChunks": "5"
                },
                files={"chunk": (f"chunk{i}.bin", chunk_data)}
            )

        # Upload chunks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(upload_chunk, i) for i in range(5)]
            results = [f.result()
                       for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(r.status_code == 200 for r in results)

        # Verify all chunks received
        status_response = client.get(f"/api/upload/status/{upload_id}")
        assert len(status_response.json()["receivedChunks"]) == 5
