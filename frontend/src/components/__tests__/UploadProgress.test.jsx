import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import UploadProgress from '../UploadProgress'
import { ChunkState } from '../../utils/chunkManager'

describe('UploadProgress', () => {
  it('should render progress bar', () => {
    const chunkState = new ChunkState(10)
    chunkState.markUploaded(0)
    chunkState.markUploaded(1)
    chunkState.markUploaded(2)
    
    render(
      <UploadProgress
        chunkState={chunkState}
        totalChunks={10}
        fileSize={10 * 1024 * 1024}
        uploadedBytes={3 * 1024 * 1024}
        uploadSpeed={1024 * 1024}
      />
    )
    
    expect(screen.getByText(/30\.0%/i)).toBeInTheDocument()
  })
  
  it('should display chunk status', () => {
    const chunkState = new ChunkState(5)
    chunkState.markUploaded(0)
    chunkState.markUploaded(1)
    chunkState.markFailed(2)
    chunkState.markInProgress(3)
    
    render(
      <UploadProgress
        chunkState={chunkState}
        totalChunks={5}
        fileSize={5 * 1024 * 1024}
        uploadedBytes={2 * 1024 * 1024}
        uploadSpeed={0}
      />
    )
    
    expect(screen.getByText(/2 \/ 5 chunks/i)).toBeInTheDocument()
  })
  
  it('should display upload speed and ETA', () => {
    const chunkState = new ChunkState(10)
    
    render(
      <UploadProgress
        chunkState={chunkState}
        totalChunks={10}
        fileSize={10 * 1024 * 1024}
        uploadedBytes={5 * 1024 * 1024}
        uploadSpeed={1024 * 1024} // 1MB/s
      />
    )
    
    expect(screen.getByText(/speed/i)).toBeInTheDocument()
    expect(screen.getByText(/eta/i)).toBeInTheDocument()
  })
  
  it('should show failed chunks warning', () => {
    const chunkState = new ChunkState(10)
    chunkState.markFailed(5)
    chunkState.markFailed(6)
    
    render(
      <UploadProgress
        chunkState={chunkState}
        totalChunks={10}
        fileSize={10 * 1024 * 1024}
        uploadedBytes={8 * 1024 * 1024}
        uploadSpeed={0}
      />
    )
    
    expect(screen.getByText(/2 chunk\(s\) failed/i)).toBeInTheDocument()
  })
  
  it('should return null when no chunk state', () => {
    const { container } = render(
      <UploadProgress
        chunkState={null}
        totalChunks={0}
        fileSize={0}
        uploadedBytes={0}
        uploadSpeed={0}
      />
    )
    
    expect(container.firstChild).toBeNull()
  })
})
