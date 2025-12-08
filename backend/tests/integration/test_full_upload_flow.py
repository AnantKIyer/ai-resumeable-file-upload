"""
Integration tests for full upload flow.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.integration
class TestFullUploadFlow:
    """Test complete upload flow from init to completion."""

    def test_complete_upload_flow(self, client: TestClient):
        """Test complete upload flow with all steps."""
        # Step 1: Initialize (use .bin extension to avoid JSONL validation)
        init_response = client.post(
            "/api/upload/init",
            json={
                "filename": "integration_test.bin",
                "totalSize": 5 * 1024 * 1024,
                "checksum": "test-checksum"
            }
        )
        assert init_response.status_code == 200
        upload_id = init_response.json()["uploadId"]
        chunk_size = init_response.json()["chunkSize"]

        # Step 2: Upload chunks
        chunk_data = b"x" * chunk_size
        total_chunks = 5

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
            assert response.json()["success"] is True

        # Step 3: Check status
        status_response = client.get(f"/api/upload/status/{upload_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["isComplete"] is True
        assert len(status_data["receivedChunks"]) == total_chunks

        # Step 4: Complete upload
        complete_response = client.post(f"/api/upload/complete/{upload_id}")
        assert complete_response.status_code == 200
        complete_data = complete_response.json()
        assert complete_data["success"] is True
        assert complete_data["metadata"]["filename"] == "integration_test.bin"
        # .bin is not a recognized type
        assert complete_data["metadata"]["fileType"] == "unknown"

    def test_resume_upload_flow(self, client: TestClient):
        """Test resuming an interrupted upload."""
        # Initialize
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "resume_test.bin",
                  "totalSize": 5 * 1024 * 1024}
        )
        upload_id = init_response.json()["uploadId"]

        # Upload some chunks
        chunk_data = b"y" * (1024 * 1024)
        for i in range(3):
            client.post(
                "/api/upload/chunk",
                data={
                    "uploadId": upload_id,
                    "chunkIndex": str(i),
                    "totalChunks": "5"
                },
                files={"chunk": (f"chunk{i}.bin", chunk_data)}
            )

        # Check status (simulating resume check)
        status_response = client.get(f"/api/upload/status/{upload_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert len(status_data["receivedChunks"]) == 3
        assert status_data["isComplete"] is False

        # Resume: upload remaining chunks
        for i in range(3, 5):
            response = client.post(
                "/api/upload/chunk",
                data={
                    "uploadId": upload_id,
                    "chunkIndex": str(i),
                    "totalChunks": "5"
                },
                files={"chunk": (f"chunk{i}.bin", chunk_data)}
            )
            assert response.status_code == 200

        # Complete
        complete_response = client.post(f"/api/upload/complete/{upload_id}")
        assert complete_response.status_code == 200

    def test_idempotent_chunk_upload(self, client: TestClient):
        """Test that uploading same chunk multiple times is safe."""
        # Initialize
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "idempotent_test.bin",
                  "totalSize": 2 * 1024 * 1024}
        )
        upload_id = init_response.json()["uploadId"]

        chunk_data = b"z" * (1024 * 1024)

        # Upload same chunk 3 times
        for _ in range(3):
            response = client.post(
                "/api/upload/chunk",
                data={
                    "uploadId": upload_id,
                    "chunkIndex": "0",
                    "totalChunks": "2"
                },
                files={"chunk": ("chunk.bin", chunk_data)}
            )
            assert response.status_code == 200

        # Upload second chunk
        client.post(
            "/api/upload/chunk",
            data={
                "uploadId": upload_id,
                "chunkIndex": "1",
                "totalChunks": "2"
            },
            files={"chunk": ("chunk1.bin", chunk_data)}
        )

        # Should be able to complete
        complete_response = client.post(f"/api/upload/complete/{upload_id}")
        assert complete_response.status_code == 200

    def test_multiple_uploads_concurrent(self, client: TestClient):
        """Test multiple uploads happening concurrently."""
        import concurrent.futures

        def upload_file(file_num):
            # Initialize (use .bin to avoid validation)
            init_response = client.post(
                "/api/upload/init",
                json={
                    "filename": f"concurrent_{file_num}.bin",
                    "totalSize": 2 * 1024 * 1024
                }
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
                        "totalChunks": "2"
                    },
                    files={"chunk": (f"chunk{i}.bin", chunk_data)}
                )

            # Complete
            return client.post(f"/api/upload/complete/{upload_id}")

        # Run 5 uploads concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(upload_file, i) for i in range(5)]
            results = [f.result()
                       for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(r.status_code == 200 for r in results)

    def test_out_of_order_chunk_upload(self, client: TestClient):
        """Test uploading chunks out of order."""
        # Initialize (use .bin to avoid validation)
        init_response = client.post(
            "/api/upload/init",
            json={"filename": "out_of_order.bin",
                  "totalSize": 5 * 1024 * 1024}
        )
        upload_id = init_response.json()["uploadId"]

        chunk_data = b"x" * (1024 * 1024)

        # Upload chunks out of order: 2, 0, 4, 1, 3
        order = [2, 0, 4, 1, 3]
        for i in order:
            response = client.post(
                "/api/upload/chunk",
                data={
                    "uploadId": upload_id,
                    "chunkIndex": str(i),
                    "totalChunks": "5"
                },
                files={"chunk": (f"chunk{i}.bin", chunk_data)}
            )
            assert response.status_code == 200

        # Should be able to complete
        complete_response = client.post(f"/api/upload/complete/{upload_id}")
        assert complete_response.status_code == 200
