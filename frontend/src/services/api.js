/**
 * API client for backend endpoints.
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Initialize an upload session.
 * @param {string} filename - Name of the file
 * @param {number} totalSize - Total file size in bytes
 * @param {string} [checksum] - Optional checksum
 * @returns {Promise<{uploadId: string, chunkSize: number}>}
 */
export const initUpload = async (filename, totalSize, checksum = null) => {
  const response = await api.post('/api/upload/init', {
    filename,
    totalSize,
    checksum,
  });
  return response.data;
};

/**
 * Upload a single chunk.
 * @param {string} uploadId - Upload session ID
 * @param {number} chunkIndex - Zero-based chunk index
 * @param {number} totalChunks - Total number of chunks
 * @param {Blob} chunkData - Chunk binary data
 * @returns {Promise<{success: boolean, receivedChunks: number, message: string}>}
 */
export const uploadChunk = async (uploadId, chunkIndex, totalChunks, chunkData) => {
  const formData = new FormData();
  formData.append('uploadId', uploadId);
  formData.append('chunkIndex', chunkIndex.toString());
  formData.append('totalChunks', totalChunks.toString());
  formData.append('chunk', chunkData);

  const response = await api.post('/api/upload/chunk', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * Get upload status.
 * @param {string} uploadId - Upload session ID
 * @returns {Promise<{uploadId: string, totalChunks: number, receivedChunks: number[], isComplete: boolean}>}
 */
export const getUploadStatus = async (uploadId) => {
  const response = await api.get(`/api/upload/status/${uploadId}`);
  return response.data;
};

/**
 * Complete an upload.
 * @param {string} uploadId - Upload session ID
 * @returns {Promise<{success: boolean, filepath: string, metadata: object, downstreamJobId: string|null, message: string}>}
 */
export const completeUpload = async (uploadId) => {
  const response = await api.post(`/api/upload/complete/${uploadId}`);
  return response.data;
};

export default api;

