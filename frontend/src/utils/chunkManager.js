/**
 * Chunk manager for file splitting, state tracking, and resume logic.
 */

/**
 * Split a file into chunks.
 * @param {File} file - File to split
 * @param {number} chunkSize - Size of each chunk in bytes
 * @returns {Blob[]} Array of chunk blobs
 */
export const splitFile = (file, chunkSize) => {
  const chunks = [];
  let start = 0;

  while (start < file.size) {
    const end = Math.min(start + chunkSize, file.size);
    const chunk = file.slice(start, end);
    chunks.push(chunk);
    start = end;
  }

  return chunks;
};

/**
 * Chunk state manager for tracking upload progress.
 */
export class ChunkState {
  constructor(totalChunks) {
    this.totalChunks = totalChunks;
    this.uploaded = new Set();
    this.failed = new Set();
    this.inProgress = new Set();
  }

  /**
   * Mark a chunk as uploaded.
   * @param {number} index - Chunk index
   */
  markUploaded(index) {
    this.uploaded.add(index);
    this.failed.delete(index);
    this.inProgress.delete(index);
  }

  /**
   * Mark a chunk as failed.
   * @param {number} index - Chunk index
   */
  markFailed(index) {
    this.failed.add(index);
    this.inProgress.delete(index);
    this.uploaded.delete(index);
  }

  /**
   * Mark a chunk as in progress.
   * @param {number} index - Chunk index
   */
  markInProgress(index) {
    this.inProgress.add(index);
    this.failed.delete(index);
  }

  /**
   * Mark a chunk as not in progress (for retry).
   * @param {number} index - Chunk index
   */
  markNotInProgress(index) {
    this.inProgress.delete(index);
  }

  /**
   * Get list of missing chunk indices.
   * @returns {number[]} Array of missing chunk indices
   */
  getMissingChunks() {
    const allChunks = new Set(
      Array.from({ length: this.totalChunks }, (_, i) => i)
    );
    const completed = new Set([...this.uploaded]);
    return Array.from(allChunks).filter((i) => !completed.has(i));
  }

  /**
   * Get list of failed chunk indices.
   * @returns {number[]} Array of failed chunk indices
   */
  getFailedChunks() {
    return Array.from(this.failed);
  }

  /**
   * Check if all chunks are uploaded.
   * @returns {boolean}
   */
  isComplete() {
    return this.uploaded.size === this.totalChunks;
  }

  /**
   * Get upload progress percentage.
   * @returns {number} Progress percentage (0-100)
   */
  getProgress() {
    return (this.uploaded.size / this.totalChunks) * 100;
  }

  /**
   * Merge server state with local state.
   * @param {number[]} serverReceivedChunks - Chunk indices received by server
   */
  mergeServerState(serverReceivedChunks) {
    // Mark all server-received chunks as uploaded
    const serverSet = new Set(serverReceivedChunks);
    serverReceivedChunks.forEach((index) => {
      this.uploaded.add(index);
      this.failed.delete(index);
      this.inProgress.delete(index);
    });
    // Clear failed status for chunks that server has received
    this.failed.forEach((index) => {
      if (serverSet.has(index)) {
        this.failed.delete(index);
      }
    });
  }

  /**
   * Reset failed chunks for retry.
   */
  resetFailed() {
    this.failed.clear();
  }

  /**
   * Get state summary.
   * @returns {object} State summary
   */
  getSummary() {
    return {
      total: this.totalChunks,
      uploaded: this.uploaded.size,
      failed: this.failed.size,
      inProgress: this.inProgress.size,
      progress: this.getProgress(),
      isComplete: this.isComplete(),
    };
  }
}

/**
 * Save upload state to localStorage.
 * @param {string} uploadId - Upload session ID
 * @param {ChunkState} chunkState - Chunk state to save
 * @param {string} filename - File name
 * @param {number} fileSize - File size
 */
export const saveStateToLocalStorage = (
  uploadId,
  chunkState,
  filename,
  fileSize
) => {
  const state = {
    uploadId,
    filename,
    fileSize,
    uploaded: Array.from(chunkState.uploaded),
    failed: Array.from(chunkState.failed),
    timestamp: Date.now(),
  };

  try {
    localStorage.setItem(`upload_${uploadId}`, JSON.stringify(state));
  } catch (e) {
    console.warn("Failed to save state to localStorage:", e);
  }
};

/**
 * Load upload state from localStorage.
 * @param {string} uploadId - Upload session ID
 * @returns {object|null} Saved state or null
 */
export const loadStateFromLocalStorage = (uploadId) => {
  try {
    const saved = localStorage.getItem(`upload_${uploadId}`);
    if (saved) {
      const state = JSON.parse(saved);
      return {
        uploaded: new Set(state.uploaded || []),
        failed: new Set(state.failed || []),
        filename: state.filename,
        fileSize: state.fileSize,
      };
    }
  } catch (e) {
    console.warn("Failed to load state from localStorage:", e);
  }
  return null;
};

/**
 * Clear upload state from localStorage.
 * @param {string} uploadId - Upload session ID
 */
export const clearStateFromLocalStorage = (uploadId) => {
  try {
    localStorage.removeItem(`upload_${uploadId}`);
  } catch (e) {
    console.warn("Failed to clear state from localStorage:", e);
  }
};
