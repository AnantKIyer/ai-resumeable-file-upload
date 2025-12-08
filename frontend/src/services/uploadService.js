/**
 * Upload service with parallel chunk uploads, retry logic, and resume capability.
 */
import * as api from './api';
import { splitFile, ChunkState, saveStateToLocalStorage, loadStateFromLocalStorage, clearStateFromLocalStorage } from '../utils/chunkManager';

const DEFAULT_CHUNK_SIZE = 1024 * 1024; // 1MB
const MAX_CONCURRENT_UPLOADS = 5;
const MAX_RETRIES = 3;
const RETRY_DELAY_BASE = 1000; // 1 second base delay

/**
 * Sleep utility for retry delays.
 * @param {number} ms - Milliseconds to sleep
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Calculate exponential backoff delay.
 * @param {number} attempt - Retry attempt number (0-indexed)
 * @returns {number} Delay in milliseconds
 */
const getRetryDelay = (attempt) => {
  return RETRY_DELAY_BASE * Math.pow(2, attempt);
};

/**
 * Upload a single chunk with retry logic.
 * @param {string} uploadId - Upload session ID
 * @param {number} chunkIndex - Chunk index
 * @param {Blob} chunkData - Chunk data
 * @param {number} totalChunks - Total number of chunks
 * @param {number} retries - Number of retries remaining
 * @returns {Promise<boolean>} Success status
 */
const uploadChunkWithRetry = async (uploadId, chunkIndex, chunkData, totalChunks, retries = MAX_RETRIES) => {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      await api.uploadChunk(uploadId, chunkIndex, totalChunks, chunkData);
      return true;
    } catch (error) {
      const isLastAttempt = attempt === retries;
      
      if (isLastAttempt) {
        console.error(`Failed to upload chunk ${chunkIndex} after ${retries + 1} attempts:`, error);
        return false;
      }
      
      // Exponential backoff
      const delay = getRetryDelay(attempt);
      console.warn(`Retrying chunk ${chunkIndex} in ${delay}ms (attempt ${attempt + 1}/${retries + 1})`);
      await sleep(delay);
    }
  }
  return false;
};

/**
 * Process upload queue with concurrency limit.
 * @param {Array} queue - Queue of upload tasks
 * @param {number} concurrency - Maximum concurrent uploads
 * @param {Function} onProgress - Progress callback
 * @returns {Promise<void>}
 */
const processUploadQueue = async (queue, concurrency, onProgress) => {
  let active = 0;
  let index = 0;
  
  const processNext = async () => {
    if (index >= queue.length || active >= concurrency) {
      return;
    }
    
    active++;
    const task = queue[index++];
    
    try {
      const success = await task();
      if (!success && onProgress) {
        onProgress(task.chunkIndex, 'failed');
      }
    } catch (error) {
      console.error(`Error processing chunk ${task.chunkIndex}:`, error);
      if (onProgress) {
        onProgress(task.chunkIndex, 'failed');
      }
    } finally {
      active--;
      if (index < queue.length) {
        await processNext();
      }
    }
  };
  
  // Start initial batch
  const initialBatch = Math.min(concurrency, queue.length);
  const promises = [];
  for (let i = 0; i < initialBatch; i++) {
    promises.push(processNext());
  }
  
  await Promise.all(promises);
};

/**
 * Upload a file with chunking, parallel uploads, and resume support.
 * @param {File} file - File to upload
 * @param {Object} options - Upload options
 * @param {number} [options.chunkSize] - Chunk size in bytes
 * @param {number} [options.concurrency] - Max concurrent uploads
 * @param {Function} [options.onProgress] - Progress callback (chunkIndex, status)
 * @param {Function} [options.onChunkComplete] - Chunk complete callback (chunkIndex)
 * @param {Function} [options.onError] - Error callback (error)
 * @returns {Promise<{uploadId: string, result: object}>}
 */
export const uploadFile = async (file, options = {}) => {
  const {
    chunkSize = DEFAULT_CHUNK_SIZE,
    concurrency = MAX_CONCURRENT_UPLOADS,
    onProgress,
    onChunkComplete,
    onError,
  } = options;
  
  try {
    // Step 1: Initialize upload
    const { uploadId, chunkSize: serverChunkSize } = await api.initUpload(
      file.name,
      file.size
    );
    
    const actualChunkSize = serverChunkSize || chunkSize;
    
    // Step 2: Split file into chunks
    const chunks = splitFile(file, actualChunkSize);
    const totalChunks = chunks.length;
    
    // Step 3: Initialize chunk state
    const chunkState = new ChunkState(totalChunks);
    
    // Step 4: Check for resume (server state)
    try {
      const serverStatus = await api.getUploadStatus(uploadId);
      if (serverStatus && serverStatus.receivedChunks) {
        chunkState.mergeServerState(serverStatus.receivedChunks);
        console.log(`Resuming upload: ${chunkState.uploaded.size}/${totalChunks} chunks already uploaded`);
      }
    } catch (error) {
      console.warn('Could not get server status, starting fresh:', error);
    }
    
    // Step 5: Check localStorage for additional state
    const localState = loadStateFromLocalStorage(uploadId);
    if (localState) {
      localState.uploaded.forEach(index => chunkState.markUploaded(index));
      localState.failed.forEach(index => chunkState.markFailed(index));
    }
    
    // Step 6: Build upload queue for missing chunks
    const missingChunks = chunkState.getMissingChunks();
    const uploadQueue = missingChunks.map(chunkIndex => {
      const task = async () => {
        chunkState.markInProgress(chunkIndex);
        if (onProgress) {
          onProgress(chunkIndex, 'uploading');
        }
        
        const success = await uploadChunkWithRetry(
          uploadId,
          chunkIndex,
          chunks[chunkIndex],
          totalChunks
        );
        
        if (success) {
          chunkState.markUploaded(chunkIndex);
          if (onProgress) {
            onProgress(chunkIndex, 'uploaded');
          }
          if (onChunkComplete) {
            onChunkComplete(chunkIndex);
          }
          
          // Save state to localStorage
          saveStateToLocalStorage(uploadId, chunkState, file.name, file.size);
        } else {
          chunkState.markFailed(chunkIndex);
          if (onProgress) {
            onProgress(chunkIndex, 'failed');
          }
        }
        
        chunkState.markNotInProgress(chunkIndex);
        return success;
      };
      
      task.chunkIndex = chunkIndex;
      return task;
    });
    
    // Step 7: Process upload queue with concurrency limit
    await processUploadQueue(uploadQueue, concurrency, onProgress);
    
    // Step 8: Check if all chunks uploaded
    if (!chunkState.isComplete()) {
      const failed = chunkState.getFailedChunks();
      throw new Error(`Upload incomplete: ${failed.length} chunks failed. Failed indices: ${failed.join(', ')}`);
    }
    
    // Step 9: Complete upload
    const result = await api.completeUpload(uploadId);
    
    // Clear localStorage state on success
    clearStateFromLocalStorage(uploadId);
    
    return {
      uploadId,
      result,
    };
  } catch (error) {
    if (onError) {
      onError(error);
    }
    throw error;
  }
};

/**
 * Retry failed chunks for an existing upload.
 * @param {string} uploadId - Upload session ID
 * @param {File} file - Original file
 * @param {ChunkState} chunkState - Current chunk state
 * @param {Blob[]} chunks - File chunks
 * @param {Object} options - Upload options
 * @returns {Promise<void>}
 */
export const retryFailedChunks = async (uploadId, file, chunkState, chunks, options = {}) => {
  const {
    concurrency = MAX_CONCURRENT_UPLOADS,
    onProgress,
    onChunkComplete,
  } = options;
  
  const failedChunks = chunkState.getFailedChunks();
  if (failedChunks.length === 0) {
    return;
  }
  
  chunkState.resetFailed();
  
  const retryQueue = failedChunks.map(chunkIndex => {
    const task = async () => {
      chunkState.markInProgress(chunkIndex);
      if (onProgress) {
        onProgress(chunkIndex, 'uploading');
      }
      
      const success = await uploadChunkWithRetry(
        uploadId,
        chunkIndex,
        chunks[chunkIndex],
        chunks.length
      );
      
      if (success) {
        chunkState.markUploaded(chunkIndex);
        if (onProgress) {
          onProgress(chunkIndex, 'uploaded');
        }
        if (onChunkComplete) {
          onChunkComplete(chunkIndex);
        }
      } else {
        chunkState.markFailed(chunkIndex);
        if (onProgress) {
          onProgress(chunkIndex, 'failed');
        }
      }
      
      chunkState.markNotInProgress(chunkIndex);
      return success;
    };
    
    task.chunkIndex = chunkIndex;
    return task;
  });
  
  await processUploadQueue(retryQueue, concurrency, onProgress);
};

