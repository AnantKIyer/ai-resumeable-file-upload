import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import * as api from '../api';

// Mock axios
vi.mock('axios');

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  
  describe('initUpload', () => {
    it('should initialize upload successfully', async () => {
      const mockResponse = {
        data: {
          uploadId: 'test-123',
          chunkSize: 1048576,
        },
      };
      
      axios.create().post.mockResolvedValue(mockResponse);
      
      const result = await api.initUpload('test.jsonl', 5242880, 'checksum-123');
      
      expect(result).toEqual(mockResponse.data);
      expect(axios.create().post).toHaveBeenCalledWith('/api/upload/init', {
        filename: 'test.jsonl',
        totalSize: 5242880,
        checksum: 'checksum-123',
      });
    });
    
    it('should initialize upload without checksum', async () => {
      const mockResponse = {
        data: {
          uploadId: 'test-456',
          chunkSize: 1048576,
        },
      };
      
      axios.create().post.mockResolvedValue(mockResponse);
      
      const result = await api.initUpload('test.jsonl', 5242880);
      
      expect(result).toEqual(mockResponse.data);
      expect(axios.create().post).toHaveBeenCalledWith('/api/upload/init', {
        filename: 'test.jsonl',
        totalSize: 5242880,
        checksum: null,
      });
    });
  });
  
  describe('uploadChunk', () => {
    it('should upload chunk successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          receivedChunks: 1,
          message: 'Chunk uploaded successfully',
        },
      };
      
      const chunkData = new Blob(['chunk data']);
      axios.create().post.mockResolvedValue(mockResponse);
      
      const result = await api.uploadChunk('test-123', 0, 5, chunkData);
      
      expect(result).toEqual(mockResponse.data);
      expect(axios.create().post).toHaveBeenCalledWith(
        '/api/upload/chunk',
        expect.any(FormData),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'multipart/form-data',
          }),
        })
      );
    });
  });
  
  describe('getUploadStatus', () => {
    it('should get upload status successfully', async () => {
      const mockResponse = {
        data: {
          uploadId: 'test-123',
          totalChunks: 5,
          receivedChunks: [0, 1, 2],
          isComplete: false,
        },
      };
      
      axios.create().get.mockResolvedValue(mockResponse);
      
      const result = await api.getUploadStatus('test-123');
      
      expect(result).toEqual(mockResponse.data);
      expect(axios.create().get).toHaveBeenCalledWith('/api/upload/status/test-123');
    });
  });
  
  describe('completeUpload', () => {
    it('should complete upload successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          filepath: 'completed/test.jsonl',
          metadata: {
            filename: 'test.jsonl',
            size: 5242880,
          },
          message: 'Upload completed successfully',
        },
      };
      
      axios.create().post.mockResolvedValue(mockResponse);
      
      const result = await api.completeUpload('test-123');
      
      expect(result).toEqual(mockResponse.data);
      expect(axios.create().post).toHaveBeenCalledWith('/api/upload/complete/test-123');
    });
  });
  
  describe('error handling', () => {
    it('should handle network errors', async () => {
      axios.create().post.mockRejectedValue(new Error('Network Error'));
      
      await expect(api.initUpload('test.jsonl', 1024)).rejects.toThrow('Network Error');
    });
    
    it('should handle server errors', async () => {
      const errorResponse = {
        response: {
          status: 500,
          data: { detail: 'Internal server error' },
        },
      };
      
      axios.create().post.mockRejectedValue(errorResponse);
      
      await expect(api.initUpload('test.jsonl', 1024)).rejects.toEqual(errorResponse);
    });
  });
});

