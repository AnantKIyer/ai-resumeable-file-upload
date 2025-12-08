# Comprehensive Test Suite Documentation

This document describes the complete test suite for the Resumable AI File Upload System.

## Overview

The test suite provides comprehensive coverage including:
- **Unit Tests**: Individual component testing
- **Integration Tests**: API and service integration
- **E2E Tests**: Full user workflow testing
- **Stress Tests**: High load and performance testing
- **Edge Case Tests**: Boundary conditions and error scenarios

## Test Coverage

### Backend Tests

#### Unit Tests (`backend/tests/unit/`)
- **test_storage.py**: Filesystem operations, chunk storage, reassembly
  - Chunk storage and retrieval
  - Atomic writes
  - File reassembly
  - Cleanup operations
  - Idempotency
  
- **test_upload_service.py**: Upload session management
  - Session creation and tracking
  - Chunk upload with idempotency
  - Status checking
  - Upload completion
  - File type detection
  
- **test_ai_integration.py**: AI integration hooks
  - Dataset validation
  - Schema validation
  - Security scanning
  - Metadata generation
  - Pipeline integration

#### API Tests (`backend/tests/api/`)
- **test_api_endpoints.py**: Full API integration
  - POST /api/upload/init
  - POST /api/upload/chunk
  - GET /api/upload/status/{uploadId}
  - POST /api/upload/complete/{uploadId}
  - Error handling
  - Concurrent operations
  - Edge cases (empty files, special characters, etc.)

#### Stress Tests (`backend/tests/stress/`)
- **test_stress.py**: Performance and load testing
  - Multiple concurrent uploads
  - Large number of chunks
  - Rapid status checks
  - Memory efficiency
  - Upload throughput benchmarks
  - Reassembly performance
  - Idempotency performance

### Frontend Tests

#### Unit Tests
- **chunkManager.test.js**: File splitting and state management
- **api.test.js**: API client functions
- **uploadService.test.js**: Upload logic and retry mechanisms
- **FileUploader.test.jsx**: Main upload component
- **UploadProgress.test.jsx**: Progress visualization

#### E2E Tests (`frontend/tests/e2e/`)
- **upload.spec.js**: Full user workflows
  - File upload flow
  - Progress tracking
  - Error handling
  - Resume functionality
  - Drag and drop
  - API integration

## Running Tests

### Backend

```bash
# All tests
cd backend
pytest

# Specific categories
pytest -m unit          # Unit tests only
pytest -m api          # API tests only
pytest -m stress       # Stress tests (slow)
pytest -m performance  # Performance tests

# With coverage
pytest --cov=app --cov-report=html

# Verbose output
pytest -v
```

### Frontend

```bash
# Unit tests
cd frontend
npm test

# Watch mode
npm test -- --watch

# Coverage
npm run test:coverage

# UI mode
npm run test:ui

# E2E tests
npm run test:e2e
```

## Test Scenarios

### Happy Path
1. User selects file
2. File is chunked
3. Chunks uploaded in parallel
4. Upload completes
5. File reassembled
6. Success message displayed

### Error Scenarios
1. Network failure during upload
2. Server error
3. Invalid file format
4. Missing chunks
5. Invalid chunk index
6. Upload session not found

### Edge Cases
1. Empty file upload
2. Single chunk file
3. Very large file (10GB+)
4. Special characters in filename
5. Concurrent uploads
6. Rapid status checks
7. Idempotent chunk uploads

### Resume Scenarios
1. Page reload during upload
2. Network interruption
3. Server restart
4. Partial chunk uploads
5. Failed chunk retry

## Performance Benchmarks

### Upload Throughput
- Target: >10 MB/s for sequential uploads
- Target: >50 MB/s for parallel uploads (5 concurrent)

### Reassembly Speed
- Target: <1 second for 100 chunks (100MB)

### Status Check Latency
- Target: <100ms per request
- Target: >100 requests/second

### Memory Usage
- Target: <500MB for 50 concurrent uploads

## Continuous Integration

Tests run automatically on:
- **Pull Requests**: All test categories
- **Main Branch**: Full test suite
- **Nightly**: Full suite including stress tests

See `.github/workflows/test.yml` for CI configuration.

## Test Data

### Test Files
- Small file: 1MB (1 chunk)
- Medium file: 5MB (5 chunks)
- Large file: 50MB (50 chunks)
- Very large file: 100MB+ (100+ chunks)

### Test Patterns
- Valid JSONL datasets
- Invalid JSONL (malformed)
- Model artifacts (.pt, .onnx)
- Archives (.zip, .tar.gz)
- Empty files
- Files with special characters

## Debugging Tests

### Backend
```bash
# Run with debugger
pytest --pdb

# Run specific test
pytest tests/unit/test_storage.py::TestStorage::test_store_chunk

# Show print statements
pytest -s
```

### Frontend
```bash
# Debug mode
npm test -- --inspect-brk

# Run specific test file
npm test chunkManager.test.js
```

### E2E
```bash
# Run in headed mode
npm run test:e2e -- --headed

# Debug mode
npm run test:e2e -- --debug

# Run specific test
npm run test:e2e -- upload.spec.js
```

## Coverage Reports

### Backend
- HTML report: `backend/htmlcov/index.html`
- XML report: `backend/coverage.xml`
- Terminal: Shown after test run

### Frontend
- HTML report: `frontend/coverage/index.html`
- JSON report: `frontend/coverage/coverage-final.json`

## Best Practices

1. **Isolation**: Each test should be independent
2. **Fixtures**: Use pytest fixtures for setup/teardown
3. **Mocking**: Mock external dependencies
4. **Assertions**: Use descriptive assertion messages
5. **Naming**: Clear, descriptive test names
6. **Speed**: Keep unit tests fast (<1s each)
7. **Coverage**: Aim for >80% code coverage

## Troubleshooting

### Backend Tests Failing
- Check Python version (3.9+)
- Verify dependencies installed
- Check temp directory permissions
- Review test logs for errors

### Frontend Tests Failing
- Check Node.js version (16+)
- Verify dependencies installed
- Clear node_modules and reinstall
- Check for port conflicts

### E2E Tests Failing
- Ensure backend is running
- Check Playwright browsers installed
- Verify network connectivity
- Review browser console logs

## Contributing

When adding new features:
1. Write tests first (TDD)
2. Ensure all tests pass
3. Maintain or improve coverage
4. Update test documentation
5. Add edge case tests

## Test Maintenance

- Review and update tests monthly
- Remove obsolete tests
- Add tests for bug fixes
- Update tests for API changes
- Monitor test execution time

