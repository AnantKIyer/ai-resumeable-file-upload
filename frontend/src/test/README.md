# Frontend Test Suite

Comprehensive test suite for the resumable file upload frontend.

## Test Structure

```
src/
├── utils/__tests__/          # Unit tests for utilities
├── services/__tests__/       # Unit tests for services
├── components/__tests__/     # Component tests
└── test/                     # Test utilities and setup
```

## Running Tests

### Run all tests
```bash
npm test
```

### Run in watch mode
```bash
npm test -- --watch
```

### Run with UI
```bash
npm run test:ui
```

### Run with coverage
```bash
npm run test:coverage
```

### Run E2E tests
```bash
npm run test:e2e
```

## Test Categories

### Unit Tests
- `chunkManager.test.js`: Chunk splitting and state management
- `uploadService.test.js`: Upload service logic

### Component Tests
- `FileUploader.test.jsx`: Main upload component
- `UploadProgress.test.jsx`: Progress visualization

### E2E Tests (`e2e/`)
- `upload.spec.js`: End-to-end upload flows
  - File selection
  - Upload process
  - Progress tracking
  - Error handling
  - Resume functionality

## Test Utilities

### `test/utils.jsx`
- `renderWithProviders`: Custom render with providers
- `createMockFile`: Create mock File objects
- `createMockChunk`: Create mock Blob chunks
- `waitForAsync`: Wait for async operations

## Coverage Goals

- Unit tests: >85% coverage
- Component tests: Cover all user interactions
- E2E tests: Cover critical user flows

## Continuous Integration

Tests run automatically on:
- Pull requests
- Commits to main branch
- Before deployment

