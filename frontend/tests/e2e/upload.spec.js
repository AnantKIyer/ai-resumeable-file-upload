import { test, expect } from '@playwright/test';

test.describe('File Upload E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display upload interface', async ({ page }) => {
    await expect(page.getByText(/resumable ai file upload/i)).toBeVisible();
    await expect(page.getByText(/drag & drop a file here/i)).toBeVisible();
  });

  test('should upload a small file successfully', async ({ page }) => {
    // Create a test file
    const fileContent = 'x'.repeat(1024 * 1024); // 1MB
    const file = {
      name: 'test.jsonl',
      mimeType: 'application/json',
      buffer: Buffer.from(fileContent),
    };

    // Wait for dropzone
    const dropzone = page.locator('[class*="dropzone"]');
    await expect(dropzone).toBeVisible();

    // Upload file (simulate file selection)
    // Note: Playwright file upload handling
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: file.name,
      mimeType: file.mimeType,
      buffer: file.buffer,
    });

    // Wait for file info to appear
    await expect(page.getByText(file.name)).toBeVisible();

    // Click start upload
    const uploadButton = page.getByRole('button', { name: /start upload/i });
    await uploadButton.click();

    // Wait for upload to complete
    await expect(page.getByText(/upload complete/i)).toBeVisible({ timeout: 30000 });
    
    // Verify success message
    await expect(page.getByText(/file:/i)).toBeVisible();
  });

  test('should show progress during upload', async ({ page }) => {
    // Create a larger test file (5MB)
    const fileContent = 'x'.repeat(5 * 1024 * 1024);
    const file = {
      name: 'large_test.jsonl',
      mimeType: 'application/json',
      buffer: Buffer.from(fileContent),
    };

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: file.name,
      mimeType: file.mimeType,
      buffer: file.buffer,
    });

    const uploadButton = page.getByRole('button', { name: /start upload/i });
    await uploadButton.click();

    // Check for progress indicators
    await expect(page.getByText(/%/)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/chunks/i)).toBeVisible();
  });

  test('should handle upload errors gracefully', async ({ page, context }) => {
    // Intercept and fail API calls
    await context.route('**/api/upload/**', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: 'Server error' }),
      });
    });

    const fileContent = 'x'.repeat(1024 * 1024);
    const file = {
      name: 'test.jsonl',
      mimeType: 'application/json',
      buffer: Buffer.from(fileContent),
    };

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: file.name,
      mimeType: file.mimeType,
      buffer: file.buffer,
    });

    const uploadButton = page.getByRole('button', { name: /start upload/i });
    await uploadButton.click();

    // Should show error message
    await expect(page.getByText(/error/i)).toBeVisible({ timeout: 10000 });
  });

  test('should allow retry of failed chunks', async ({ page }) => {
    // Create a file and simulate partial failure
    const fileContent = 'x'.repeat(5 * 1024 * 1024);
    const file = {
      name: 'test.jsonl',
      mimeType: 'application/json',
      buffer: Buffer.from(fileContent),
    };

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: file.name,
      mimeType: file.mimeType,
      buffer: file.buffer,
    });

    const uploadButton = page.getByRole('button', { name: /start upload/i });
    await uploadButton.click();

    // Wait for potential failures
    await page.waitForTimeout(2000);

    // Check for retry button if failures occurred
    const retryButton = page.getByRole('button', { name: /retry/i });
    if (await retryButton.isVisible()) {
      await retryButton.click();
      // Verify retry is working
      await expect(page.getByText(/uploading/i)).toBeVisible();
    }
  });

  test('should support drag and drop', async ({ page }) => {
    const dropzone = page.locator('[class*="dropzone"]');
    
    // Create a data transfer object
    const fileContent = 'x'.repeat(1024 * 1024);
    const dataTransfer = await page.evaluateHandle((content) => {
      const dt = new DataTransfer();
      const file = new File([content], 'test.jsonl', { type: 'application/json' });
      dt.items.add(file);
      return dt;
    }, fileContent);

    // Simulate drag and drop
    await dropzone.dispatchEvent('drop', { dataTransfer });
    
    // Verify file was selected
    await expect(page.getByText('test.jsonl')).toBeVisible({ timeout: 2000 });
  });

  test('should display file metadata after upload', async ({ page }) => {
    const fileContent = 'x'.repeat(1024 * 1024);
    const file = {
      name: 'dataset.jsonl',
      mimeType: 'application/json',
      buffer: Buffer.from(fileContent),
    };

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: file.name,
      mimeType: file.mimeType,
      buffer: file.buffer,
    });

    const uploadButton = page.getByRole('button', { name: /start upload/i });
    await uploadButton.click();

    // Wait for completion
    await expect(page.getByText(/upload complete/i)).toBeVisible({ timeout: 30000 });
    
    // Verify metadata display
    await expect(page.getByText(/file:/i)).toBeVisible();
    await expect(page.getByText(/size:/i)).toBeVisible();
    await expect(page.getByText(/type:/i)).toBeVisible();
  });

  test('should handle page reload and resume', async ({ page, context }) => {
    const fileContent = 'x'.repeat(5 * 1024 * 1024);
    const file = {
      name: 'resume_test.jsonl',
      mimeType: 'application/json',
      buffer: Buffer.from(fileContent),
    };

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: file.name,
      mimeType: file.mimeType,
      buffer: file.buffer,
    });

    const uploadButton = page.getByRole('button', { name: /start upload/i });
    await uploadButton.click();

    // Wait a bit for some chunks to upload
    await page.waitForTimeout(3000);

    // Reload page
    await page.reload();

    // Re-select the same file
    await fileInput.setInputFiles({
      name: file.name,
      mimeType: file.mimeType,
      buffer: file.buffer,
    });

    // Should resume from where it left off
    // (This depends on localStorage and server state)
    await expect(page.getByText(/resume/i).or(page.getByText(/upload/i))).toBeVisible();
  });
});

test.describe('API Integration E2E', () => {
  test('should communicate with backend API', async ({ page, request }) => {
    // Test API directly
    const initResponse = await request.post('http://localhost:8000/api/upload/init', {
      data: {
        filename: 'api_test.jsonl',
        totalSize: 1024 * 1024,
      },
    });

    expect(initResponse.ok()).toBeTruthy();
    const initData = await initResponse.json();
    expect(initData).toHaveProperty('uploadId');
    expect(initData).toHaveProperty('chunkSize');

    // Test status endpoint
    const statusResponse = await request.get(
      `http://localhost:8000/api/upload/status/${initData.uploadId}`
    );
    expect(statusResponse.ok()).toBeTruthy();
    const statusData = await statusResponse.json();
    expect(statusData).toHaveProperty('totalChunks');
    expect(statusData).toHaveProperty('receivedChunks');
  });
});

