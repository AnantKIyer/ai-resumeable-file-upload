# Backend Test Suite

Comprehensive test suite for the resumable file upload backend.

## Test Structure

```
tests/
├── unit/              # Unit tests for individual modules
├── integration/        # Integration tests for full flows
├── api/               # API endpoint tests
├── stress/            # Stress and load tests
└── performance/       # Performance benchmarks
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test categories
```bash
# Unit tests only
pytest -m unit

# API tests only
pytest -m api

# Integration tests
pytest -m integration

# Stress tests (slow)
pytest -m stress

# Performance tests
pytest -m performance
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html
```

### Run in parallel
```bash
pytest -n auto
```

### Run specific test file
```bash
pytest tests/unit/test_storage.py
```

## Test Categories

### Unit Tests (`tests/unit/`)
- `test_storage.py`: Storage layer tests
- `test_upload_service.py`: Upload service tests
- `test_ai_integration.py`: AI integration hooks tests

### API Tests (`tests/api/`)
- `test_api_endpoints.py`: Comprehensive API endpoint tests
  - Init upload
  - Chunk upload
  - Status checks
  - Completion
  - Edge cases

### Integration Tests (`tests/integration/`)
- `test_full_upload_flow.py`: End-to-end upload flows
  - Complete upload flow
  - Resume functionality
  - Idempotent operations
  - Concurrent uploads

### Stress Tests (`tests/stress/`)
- `test_stress.py`: Stress and load tests
  - Concurrent uploads
  - Large files
  - Many small files
  - Rapid status checks

### Performance Tests (`tests/performance/`)
- `test_performance.py`: Performance benchmarks
  - Chunk storage/retrieval
  - File reassembly
  - Concurrent operations

## Test Markers

Tests are marked with pytest markers:
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.api`: API tests
- `@pytest.mark.stress`: Stress tests
- `@pytest.mark.performance`: Performance tests
- `@pytest.mark.slow`: Slow-running tests

## Coverage Goals

- Unit tests: >90% coverage
- Integration tests: Cover all main flows
- API tests: Cover all endpoints and edge cases
- Stress tests: Verify system under load
- Performance tests: Establish baselines

## Continuous Integration

Tests run automatically on:
- Pull requests
- Commits to main branch
- Nightly builds (including stress tests)
