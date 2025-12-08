import React from 'react'
import { render } from '@testing-library/react'
import { vi } from 'vitest'

/**
 * Custom render function with providers
 */
export const renderWithProviders = (ui, options = {}) => {
  return render(ui, { ...options })
}

/**
 * Mock file for testing
 */
export const createMockFile = (name = 'test.jsonl', size = 1024, type = 'application/json') => {
  const file = new File(['x'.repeat(size)], name, { type })
  return file
}

/**
 * Mock blob for chunk testing
 */
export const createMockChunk = (size = 1024 * 1024) => {
  return new Blob(['x'.repeat(size)], { type: 'application/octet-stream' })
}

/**
 * Wait for async operations
 */
export const waitForAsync = () => new Promise(resolve => setTimeout(resolve, 0))

