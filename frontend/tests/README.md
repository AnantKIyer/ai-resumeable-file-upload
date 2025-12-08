# Frontend Test Suite

Comprehensive test suite for the resumable file upload frontend.

## Test Structure

```
tests/
├── e2e/                    # End-to-end tests (Playwright)
│   └── upload.spec.js
src/
├── components/__tests__/    # Component tests
│   ├── FileUploader.test.jsx
│   └── UploadProgress.test.jsx
├── services/__tests__/     # Service tests
│   ├── api.test.js
│   └── uploadService.test.js
└── utils/__tests__/        # Utility tests
    └── chunkManager.test.js
```

## Running Tests

### Unit Tests
```bash
npm test
```

### Watch Mode
```bash
npm test -- --watch
```

### Coverage
```bash
npm run test:coverage
```

### UI Mode
```bash
npm run test:ui
```

### E2E Tests
```bash
npm run test:e2e
```

### E2E in UI Mode
```bash
npm run test:e2e -- --ui
```

## Test Categories

### Unit Tests
- **chunkManager**: File splitting, state management, localStorage
- **api**: API client functions
- **uploadService**: Upload logic, retry, resume
- **Components**: React component rendering and interactions

### Integration Tests
- Component integration with services
- API mocking and responses
- State management flows

### E2E Tests (Playwright)
- Full upload flow
- Error handling
- Resume functionality
- Drag and drop
- Progress tracking

## Writing New Tests

### Unit Test Example
```javascript
import { describe, it, expect } from 'vitest';

describe('MyComponent', () => {
  it('should render correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
```

### E2E Test Example
```javascript
import { test, expect } from '@playwright/test';

test('should upload file', async ({ page }) => {
  await page.goto('/');
  // ... test steps
});
```

## Test Utilities

### Mocking
- `vi.mock()` for module mocking
- MSW for API mocking (if needed)

### Helpers
- `@testing-library/react` for component testing
- `@testing-library/user-event` for user interactions
- `@playwright/test` for E2E testing

## Coverage Targets

- **Statements**: >80%
- **Branches**: >75%
- **Functions**: >80%
- **Lines**: >80%

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to main branch
- Before deployment

See `.github/workflows/test.yml` for CI configuration.

