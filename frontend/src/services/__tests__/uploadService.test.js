import { describe, it, expect, beforeEach, vi } from 'vitest'
import * as api from '../api'
import { uploadFile, retryFailedChunks } from '../uploadService'
import { ChunkState } from '../../utils/chunkManager'

// Mock API
vi.mock('../api', () => ({
  initUpload: vi.fn(),
  uploadChunk: vi.fn(),
  getUploadStatus: vi.fn(),
  completeUpload: vi.fn(),
}))

describe('uploadService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })
  
  describe('uploadFile', () => {
    it('should upload file successfully', async () => {
      const file = new File(['x'.repeat(2 * 1024 * 1024)], 'test.jsonl')
      
      api.initUpload.mockResolvedValue({
        uploadId: 'test-123',
        chunkSize: 1024 * 1024
      })
      
      api.uploadChunk.mockResolvedValue({
        success: true,
        receivedChunks: 1,
        message: 'Success'
      })
      
      api.getUploadStatus.mockResolvedValue({
        uploadId: 'test-123',
        totalChunks: 2,
        receivedChunks: [],
        isComplete: false
      })
      
      api.completeUpload.mockResolvedValue({
        success: true,
        filepath: 'completed/test.jsonl',
        metadata: {
          filename: 'test.jsonl',
          size: 2 * 1024 * 1024
        }
      })
      
      const result = await uploadFile(file, {
        chunkSize: 1024 * 1024,
        concurrency: 2
      })
      
      expect(result.uploadId).toBe('test-123')
      expect(api.initUpload).toHaveBeenCalledTimes(1)
      expect(api.uploadChunk).toHaveBeenCalledTimes(2)
      expect(api.completeUpload).toHaveBeenCalledTimes(1)
    })
    
    it('should resume upload from server state', async () => {
      const file = new File(['x'.repeat(3 * 1024 * 1024)], 'resume.jsonl')
      
      api.initUpload.mockResolvedValue({
        uploadId: 'resume-123',
        chunkSize: 1024 * 1024
      })
      
      api.getUploadStatus.mockResolvedValue({
        uploadId: 'resume-123',
        totalChunks: 3,
        receivedChunks: [0, 1], // Already uploaded
        isComplete: false
      })
      
      api.uploadChunk.mockResolvedValue({
        success: true,
        receivedChunks: 3,
        message: 'Success'
      })
      
      api.completeUpload.mockResolvedValue({
        success: true,
        filepath: 'completed/resume.jsonl',
        metadata: { filename: 'resume.jsonl' }
      })
      
      await uploadFile(file)
      
      // Should only upload missing chunk (index 2)
      expect(api.uploadChunk).toHaveBeenCalledTimes(1)
      expect(api.uploadChunk).toHaveBeenCalledWith(
        'resume-123',
        2,
        3,
        expect.any(Blob)
      )
    })
    
    it('should handle upload errors', async () => {
      const file = new File(['x'.repeat(1024 * 1024)], 'error.jsonl')
      
      api.initUpload.mockResolvedValue({
        uploadId: 'error-123',
        chunkSize: 1024 * 1024
      })
      
      api.getUploadStatus.mockResolvedValue({
        uploadId: 'error-123',
        totalChunks: 1,
        receivedChunks: [],
        isComplete: false
      })
      
      api.uploadChunk.mockRejectedValue(new Error('Network error'))
      
      await expect(uploadFile(file)).rejects.toThrow()
    })
    
    it('should retry failed chunks', async () => {
      const file = new File(['x'.repeat(2 * 1024 * 1024)], 'retry.jsonl')
      
      api.initUpload.mockResolvedValue({
        uploadId: 'retry-123',
        chunkSize: 1024 * 1024
      })
      
      api.getUploadStatus.mockResolvedValue({
        uploadId: 'retry-123',
        totalChunks: 2,
        receivedChunks: [],
        isComplete: false
      })
      
      // First attempt fails, second succeeds
      api.uploadChunk
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          success: true,
          receivedChunks: 1,
          message: 'Success'
        })
        .mockResolvedValueOnce({
          success: true,
          receivedChunks: 2,
          message: 'Success'
        })
      
      api.completeUpload.mockResolvedValue({
        success: true,
        filepath: 'completed/retry.jsonl',
        metadata: { filename: 'retry.jsonl' }
      })
      
      // Use vi.useFakeTimers for retry delays
      vi.useFakeTimers()
      
      const uploadPromise = uploadFile(file, {
        chunkSize: 1024 * 1024,
        concurrency: 1
      })
      
      // Fast-forward timers
      await vi.runAllTimersAsync()
      
      await uploadPromise
      
      // Should have retried
      expect(api.uploadChunk).toHaveBeenCalledTimes(3) // 1 fail + 2 success
      
      vi.useRealTimers()
    })
  })
  
  describe('retryFailedChunks', () => {
    it('should retry failed chunks', async () => {
      const file = new File(['x'.repeat(2 * 1024 * 1024)], 'retry.jsonl')
      const chunks = [
        new Blob(['x'.repeat(1024 * 1024)]),
        new Blob(['y'.repeat(1024 * 1024)])
      ]
      const chunkState = new ChunkState(2)
      chunkState.markFailed(0)
      chunkState.markUploaded(1)
      
      api.uploadChunk.mockResolvedValue({
        success: true,
        receivedChunks: 2,
        message: 'Success'
      })
      
      await retryFailedChunks('retry-123', file, chunkState, chunks)
      
      expect(api.uploadChunk).toHaveBeenCalledWith(
        'retry-123',
        0,
        2,
        chunks[0]
      )
      expect(chunkState.uploaded.has(0)).toBe(true)
    })
  })
})
