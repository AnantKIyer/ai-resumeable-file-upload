"""
Performance benchmarks for chunk operations.
"""
import pytest
import time
from app.storage import Storage
from app.upload_service import UploadService
from app.models import InitUploadRequest


@pytest.mark.performance
class TestStoragePerformance:
    """Performance tests for storage operations."""

    def test_chunk_storage_performance(self, storage: Storage, request):
        """Benchmark chunk storage."""
        chunk_data = b"x" * (1024 * 1024)  # 1MB

        def store_chunk():
            storage.store_chunk("perf-test", 0, chunk_data)

        # Try to use benchmark if available, otherwise just test
        try:
            benchmark = request.getfixturevalue('benchmark')
            benchmark(store_chunk)
        except (pytest.FixtureLookupError, ValueError):
            # Fallback if pytest-benchmark not available
            import time
            start = time.time()
            store_chunk()
            elapsed = time.time() - start
            assert elapsed < 1.0  # Should be fast

    def test_chunk_retrieval_performance(self, storage: Storage, request):
        """Benchmark chunk retrieval."""
        # Store chunk first
        chunk_data = b"y" * (1024 * 1024)
        storage.store_chunk("perf-retrieve", 0, chunk_data)

        def retrieve_chunk():
            return storage.get_chunk("perf-retrieve", 0)

        try:
            benchmark = request.getfixturevalue('benchmark')
            result = benchmark(retrieve_chunk)
            assert result == chunk_data
        except (pytest.FixtureLookupError, ValueError):
            result = retrieve_chunk()
            assert result == chunk_data

    def test_list_chunks_performance(self, storage: Storage, request):
        """Benchmark listing chunks."""
        # Store many chunks
        for i in range(100):
            storage.store_chunk("perf-list", i, b"x" * 1000)

        def list_chunks():
            return storage.list_chunks("perf-list")

        try:
            benchmark = request.getfixturevalue('benchmark')
            result = benchmark(list_chunks)
            assert len(result) == 100
        except (pytest.FixtureLookupError, ValueError):
            result = list_chunks()
            assert len(result) == 100

    def test_reassemble_performance(self, storage: Storage, request):
        """Benchmark file reassembly."""
        # Store chunks
        chunk_data = b"z" * (1024 * 1024)
        total_chunks = 10

        for i in range(total_chunks):
            storage.store_chunk("perf-reassemble", i, chunk_data)

        def reassemble():
            return storage.reassemble_file(
                "perf-reassemble",
                total_chunks,
                "perf_output.bin"
            )

        try:
            benchmark = request.getfixturevalue('benchmark')
            result = benchmark(reassemble)
            assert result is not None
        except (pytest.FixtureLookupError, ValueError):
            result = reassemble()
            assert result is not None


@pytest.mark.performance
class TestUploadServicePerformance:
    """Performance tests for upload service."""

    def test_init_upload_performance(self, upload_service: UploadService, request):
        """Benchmark upload initialization."""
        req = InitUploadRequest(
            filename="perf.bin",
            totalSize=10 * 1024 * 1024
        )

        def init():
            return upload_service.init_upload(req)

        try:
            benchmark = request.getfixturevalue('benchmark')
            result = benchmark(init)
            assert result[0] is not None
        except (pytest.FixtureLookupError, ValueError):
            result = init()
            assert result[0] is not None

    def test_upload_chunk_performance(self, upload_service: UploadService, request):
        """Benchmark chunk upload."""
        req = InitUploadRequest(
            filename="perf.bin",
            totalSize=10 * 1024 * 1024
        )
        upload_id, _ = upload_service.init_upload(req)

        chunk_data = b"x" * (1024 * 1024)

        def upload():
            return upload_service.upload_chunk(
                upload_id, 0, chunk_data, 10
            )

        try:
            benchmark = request.getfixturevalue('benchmark')
            result = benchmark(upload)
            assert result[0] is True
        except (pytest.FixtureLookupError, ValueError):
            result = upload()
            assert result[0] is True

    def test_get_status_performance(self, upload_service: UploadService, request):
        """Benchmark status retrieval."""
        req = InitUploadRequest(
            filename="perf.bin",
            totalSize=10 * 1024 * 1024
        )
        upload_id, _ = upload_service.init_upload(req)

        # Upload some chunks
        chunk_data = b"x" * (1024 * 1024)
        for i in range(5):
            upload_service.upload_chunk(upload_id, i, chunk_data, 10)

        def get_status():
            return upload_service.get_upload_status(upload_id)

        try:
            benchmark = request.getfixturevalue('benchmark')
            result = benchmark(get_status)
            assert result is not None
        except (pytest.FixtureLookupError, ValueError):
            result = get_status()
            assert result is not None


@pytest.mark.performance
class TestConcurrentPerformance:
    """Performance tests for concurrent operations."""

    def test_concurrent_chunk_storage(self, storage: Storage):
        """Test concurrent chunk storage performance."""
        import concurrent.futures

        chunk_data = b"x" * (1024 * 1024)
        num_chunks = 50

        def store_chunk(i):
            return storage.store_chunk("concurrent-perf", i, chunk_data)

        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(store_chunk, i)
                       for i in range(num_chunks)]
            results = [f.result()
                       for f in concurrent.futures.as_completed(futures)]

        elapsed = time.time() - start
        chunks_per_second = num_chunks / elapsed

        assert all(results)
        assert chunks_per_second > 10  # At least 10 chunks/second

    def test_concurrent_status_checks(self, upload_service: UploadService):
        """Test concurrent status check performance."""
        import concurrent.futures

        request = InitUploadRequest(
            filename="concurrent-status.bin",
            totalSize=10 * 1024 * 1024
        )
        upload_id, _ = upload_service.init_upload(request)

        # Upload some chunks
        chunk_data = b"x" * (1024 * 1024)
        for i in range(5):
            upload_service.upload_chunk(upload_id, i, chunk_data, 10)

        def check_status():
            return upload_service.get_upload_status(upload_id)

        num_checks = 100
        start = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(check_status)
                       for _ in range(num_checks)]
            results = [f.result()
                       for f in concurrent.futures.as_completed(futures)]

        elapsed = time.time() - start
        checks_per_second = num_checks / elapsed

        assert all(r is not None for r in results)
        assert checks_per_second > 50  # At least 50 checks/second
