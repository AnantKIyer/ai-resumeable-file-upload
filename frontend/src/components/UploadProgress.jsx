import React from 'react';
import './UploadProgress.css';

/**
 * Upload progress component showing chunk-level status.
 */
const UploadProgress = ({ chunkState, totalChunks, fileSize, uploadedBytes, uploadSpeed }) => {
  if (!chunkState || totalChunks === 0) {
    return null;
  }
  
  const progress = chunkState.getProgress();
  const summary = chunkState.getSummary();
  
  // Calculate ETA
  const calculateETA = () => {
    if (!uploadSpeed || uploadSpeed === 0) return 'Calculating...';
    const remainingBytes = fileSize - uploadedBytes;
    const remainingSeconds = remainingBytes / uploadSpeed;
    
    if (remainingSeconds < 60) {
      return `${Math.ceil(remainingSeconds)}s`;
    } else if (remainingSeconds < 3600) {
      return `${Math.ceil(remainingSeconds / 60)}m`;
    } else {
      return `${Math.ceil(remainingSeconds / 3600)}h`;
    }
  };
  
  // Format bytes
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };
  
  // Get chunk status color
  const getChunkStatus = (index) => {
    if (chunkState.uploaded.has(index)) return 'uploaded';
    if (chunkState.failed.has(index)) return 'failed';
    if (chunkState.inProgress.has(index)) return 'uploading';
    return 'pending';
  };
  
  // Render chunk grid (show first 100 chunks to avoid performance issues)
  const maxChunksToShow = 100;
  const chunksToShow = Math.min(totalChunks, maxChunksToShow);
  const chunkWidth = 100 / chunksToShow;
  
  return (
    <div className="upload-progress">
      <div className="progress-header">
        <div className="progress-info">
          <div className="progress-text">
            <span className="progress-percentage">{progress.toFixed(1)}%</span>
            <span className="progress-stats">
              {summary.uploaded} / {summary.total} chunks
            </span>
          </div>
          <div className="progress-bar-container">
            <div 
              className="progress-bar" 
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
        <div className="progress-details">
          <div className="detail-item">
            <span className="detail-label">Uploaded:</span>
            <span className="detail-value">{formatBytes(uploadedBytes)} / {formatBytes(fileSize)}</span>
          </div>
          {uploadSpeed > 0 && (
            <>
              <div className="detail-item">
                <span className="detail-label">Speed:</span>
                <span className="detail-value">{formatBytes(uploadSpeed)}/s</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">ETA:</span>
                <span className="detail-value">{calculateETA()}</span>
              </div>
            </>
          )}
        </div>
      </div>
      
      {totalChunks > 0 && (
        <div className="chunks-grid">
          <div className="chunks-grid-header">
            <span>Chunk Status ({totalChunks > maxChunksToShow ? `Showing first ${maxChunksToShow} of ${totalChunks}` : `${totalChunks} chunks`})</span>
          </div>
          <div className="chunks-grid-container">
            {Array.from({ length: chunksToShow }, (_, i) => {
              const status = getChunkStatus(i);
              return (
                <div
                  key={i}
                  className={`chunk-indicator chunk-${status}`}
                  style={{ width: `${chunkWidth}%` }}
                  title={`Chunk ${i}: ${status}`}
                />
              );
            })}
          </div>
          <div className="chunks-legend">
            <div className="legend-item">
              <span className="legend-color chunk-uploaded" />
              <span>Uploaded ({summary.uploaded})</span>
            </div>
            <div className="legend-item">
              <span className="legend-color chunk-uploading" />
              <span>Uploading ({summary.inProgress})</span>
            </div>
            <div className="legend-item">
              <span className="legend-color chunk-failed" />
              <span>Failed ({summary.failed})</span>
            </div>
            <div className="legend-item">
              <span className="legend-color chunk-pending" />
              <span>Pending ({summary.total - summary.uploaded - summary.inProgress - summary.failed})</span>
            </div>
          </div>
        </div>
      )}
      
      {summary.failed > 0 && (
        <div className="failed-chunks-warning">
          <span>⚠️ {summary.failed} chunk(s) failed. Use retry button to re-upload failed chunks.</span>
        </div>
      )}
    </div>
  );
};

export default UploadProgress;

