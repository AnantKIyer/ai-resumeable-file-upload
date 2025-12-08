import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadFile, retryFailedChunks } from '../services/uploadService';
import { completeUpload } from '../services/api';
import { splitFile, ChunkState, loadStateFromLocalStorage, clearStateFromLocalStorage } from '../utils/chunkManager';
import UploadProgress from './UploadProgress';
import './FileUploader.css';

/**
 * Main file uploader component with drag-and-drop, chunking, and resume support.
 */
const FileUploader = () => {
  const [file, setFile] = useState(null);
  const [uploadId, setUploadId] = useState(null);
  const [chunkState, setChunkState] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isCompleting, setIsCompleting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadedBytes, setUploadedBytes] = useState(0);
  const [uploadSpeed, setUploadSpeed] = useState(0);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  
  const uploadStartTime = useRef(null);
  const lastUploadedBytes = useRef(0);
  const speedUpdateInterval = useRef(null);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (speedUpdateInterval.current) {
        clearInterval(speedUpdateInterval.current);
      }
    };
  }, []);
  
  // Update upload speed periodically
  useEffect(() => {
    if (isUploading && uploadStartTime.current) {
      speedUpdateInterval.current = setInterval(() => {
        const elapsed = (Date.now() - uploadStartTime.current) / 1000;
        if (elapsed > 0) {
          const speed = uploadedBytes / elapsed;
          setUploadSpeed(speed);
        }
      }, 1000);
    } else {
      if (speedUpdateInterval.current) {
        clearInterval(speedUpdateInterval.current);
        speedUpdateInterval.current = null;
      }
    }
  }, [isUploading, uploadedBytes]);
  
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      const selectedFile = acceptedFiles[0];
      setFile(selectedFile);
      setError(null);
      setResult(null);
      setUploadId(null);
      setChunkState(null);
      setChunks([]);
      setUploadProgress(0);
      setUploadedBytes(0);
      setUploadSpeed(0);
    }
  }, []);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    disabled: isUploading || isCompleting,
  });
  
  const handleUpload = async () => {
    if (!file) return;
    
    setIsUploading(true);
    setError(null);
    setResult(null);
    uploadStartTime.current = Date.now();
    lastUploadedBytes.current = 0;
    
    try {
      // Split file into chunks
      const fileChunks = splitFile(file, 1024 * 1024); // 1MB chunks
      setChunks(fileChunks);
      
      // Initialize chunk state
      const initialState = new ChunkState(fileChunks.length);
      setChunkState(initialState);
      
      // Calculate uploaded bytes from chunk state
      const updateUploadedBytes = () => {
        if (chunkState) {
          const uploaded = Array.from(chunkState.uploaded);
          const bytes = uploaded.reduce((sum, index) => {
            return sum + (fileChunks[index]?.size || 0);
          }, 0);
          setUploadedBytes(bytes);
        }
      };
      
      // Upload file
      const { uploadId: newUploadId, result: uploadResult } = await uploadFile(file, {
        chunkSize: 1024 * 1024,
        concurrency: 5,
        onProgress: (chunkIndex, status) => {
          setChunkState((prev) => {
            const newState = new ChunkState(fileChunks.length);
            if (prev) {
              newState.uploaded = new Set(prev.uploaded);
              newState.failed = new Set(prev.failed);
              newState.inProgress = new Set(prev.inProgress);
            }
            
            if (status === 'uploaded') {
              newState.markUploaded(chunkIndex);
            } else if (status === 'failed') {
              newState.markFailed(chunkIndex);
            } else if (status === 'uploading') {
              newState.markInProgress(chunkIndex);
            }
            
            const progress = newState.getProgress();
            setUploadProgress(progress);
            
            // Update uploaded bytes
            const uploaded = Array.from(newState.uploaded);
            const bytes = uploaded.reduce((sum, index) => {
              return sum + (fileChunks[index]?.size || 0);
            }, 0);
            setUploadedBytes(bytes);
            
            return newState;
          });
        },
        onChunkComplete: (chunkIndex) => {
          // Chunk completed
        },
        onError: (err) => {
          setError(err.message || 'Upload failed');
          setIsUploading(false);
        },
      });
      
      setUploadId(newUploadId);
      setIsUploading(false);
      setIsCompleting(true);
      
      // Wait a bit for final state update
      await new Promise(resolve => setTimeout(resolve, 500));
      
      setResult(uploadResult);
      setIsCompleting(false);
      
      // Clear any localStorage state
      clearStateFromLocalStorage(newUploadId);
    } catch (err) {
      setError(err.message || 'Upload failed');
      setIsUploading(false);
      setIsCompleting(false);
    }
  };
  
  const handleRetry = async () => {
    if (!file || !uploadId || !chunkState || chunks.length === 0) return;
    
    setIsUploading(true);
    setError(null);
    
    try {
      await retryFailedChunks(uploadId, file, chunkState, chunks, {
        concurrency: 5,
        onProgress: (chunkIndex, status) => {
          setChunkState(prev => {
            const newState = new ChunkState(chunks.length);
            if (prev) {
              newState.uploaded = new Set(prev.uploaded);
              newState.failed = new Set(prev.failed);
              newState.inProgress = new Set(prev.inProgress);
            }
            
            if (status === 'uploaded') {
              newState.markUploaded(chunkIndex);
            } else if (status === 'failed') {
              newState.markFailed(chunkIndex);
            } else if (status === 'uploading') {
              newState.markInProgress(chunkIndex);
            }
            
            const progress = newState.getProgress();
            setUploadProgress(progress);
            
            // Update uploaded bytes
            const uploaded = Array.from(newState.uploaded);
            const bytes = uploaded.reduce((sum, index) => {
              return sum + (chunks[index]?.size || 0);
            }, 0);
            setUploadedBytes(bytes);
            
            return newState;
          });
        },
      });
      
      // If all chunks are now uploaded, complete the upload
      if (chunkState.isComplete()) {
        setIsCompleting(true);
        const uploadResult = await completeUpload(uploadId);
        setResult(uploadResult);
        setIsCompleting(false);
        clearStateFromLocalStorage(uploadId);
      }
      
      setIsUploading(false);
    } catch (err) {
      setError(err.message || 'Retry failed');
      setIsUploading(false);
    }
  };
  
  const handleReset = () => {
    setFile(null);
    setUploadId(null);
    setChunkState(null);
    setChunks([]);
    setIsUploading(false);
    setIsCompleting(false);
    setUploadProgress(0);
    setUploadedBytes(0);
    setUploadSpeed(0);
    setError(null);
    setResult(null);
  };
  
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };
  
  return (
    <div className="file-uploader">
      <div className="uploader-container">
        <h1>Resumable AI File Upload</h1>
        <p className="subtitle">Upload large datasets, model artifacts, and training files with resume capability</p>
        
        {!file && (
          <div
            {...getRootProps()}
            className={`dropzone ${isDragActive ? 'active' : ''}`}
          >
            <input {...getInputProps()} />
            <div className="dropzone-content">
              <svg
                className="dropzone-icon"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              <p className="dropzone-text">
                {isDragActive
                  ? 'Drop the file here...'
                  : 'Drag & drop a file here, or click to select'}
              </p>
              <p className="dropzone-hint">Supports large files with automatic resume on failure</p>
            </div>
          </div>
        )}
        
        {file && !isUploading && !isCompleting && !result && (
          <div className="file-info">
            <div className="file-details">
              <span className="file-name">{file.name}</span>
              <span className="file-size">{formatFileSize(file.size)}</span>
            </div>
            <div className="file-actions">
              <button onClick={handleUpload} className="btn btn-primary">
                Start Upload
              </button>
              <button onClick={handleReset} className="btn btn-secondary">
                Choose Different File
              </button>
            </div>
          </div>
        )}
        
        {(isUploading || isCompleting) && chunkState && (
          <div className="upload-status">
            <UploadProgress
              chunkState={chunkState}
              totalChunks={chunks.length}
              fileSize={file.size}
              uploadedBytes={uploadedBytes}
              uploadSpeed={uploadSpeed}
            />
            {isCompleting && (
              <div className="completing-message">
                <span>⏳ Completing upload and running validation...</span>
              </div>
            )}
            {chunkState.getFailedChunks().length > 0 && !isCompleting && (
              <button onClick={handleRetry} className="btn btn-warning">
                Retry Failed Chunks ({chunkState.getFailedChunks().length})
              </button>
            )}
          </div>
        )}
        
        {error && (
          <div className="error-message">
            <span>❌ {error}</span>
            {chunkState && chunkState.getFailedChunks().length > 0 && (
              <button onClick={handleRetry} className="btn btn-warning">
                Retry Failed Chunks
              </button>
            )}
            <button onClick={handleReset} className="btn btn-secondary">
              Start Over
            </button>
          </div>
        )}
        
        {result && (
          <div className="success-message">
            <h2>✅ Upload Complete!</h2>
            <div className="result-details">
              <p><strong>File:</strong> {result.metadata.filename}</p>
              <p><strong>Size:</strong> {formatFileSize(result.metadata.size)}</p>
              <p><strong>Type:</strong> {result.metadata.fileType}</p>
              <p><strong>Path:</strong> {result.filepath}</p>
              {result.downstreamJobId && (
                <p><strong>Downstream Job ID:</strong> {result.downstreamJobId}</p>
              )}
            </div>
            <button onClick={handleReset} className="btn btn-primary">
              Upload Another File
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default FileUploader;

