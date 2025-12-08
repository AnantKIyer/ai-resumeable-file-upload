# Frontend - Resumable AI File Upload UI

React frontend for resumable chunked file uploads with drag-and-drop, progress tracking, and resume capability.

## Setup

```bash
npm install
```

## Running

```bash
# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

The frontend runs on `http://localhost:3000` and proxies API requests to `http://localhost:8000`.

## Features

### File Upload
- Drag-and-drop file selection
- Click to browse files
- Support for large files (GB+)

### Chunked Upload
- Automatic file splitting into 1MB chunks
- Parallel uploads (5 concurrent chunks)
- Real-time progress tracking

### Resume Capability
- Automatic resume on page reload
- Server state synchronization
- LocalStorage persistence (optional)
- Retry failed chunks

### Progress Visualization
- Overall progress percentage
- Chunk-level status grid
- Upload speed and ETA
- Failed chunk indicators

## Architecture

### Components

#### FileUploader
Main upload component with:
- File selection (drag-and-drop)
- Upload state management
- Error handling
- Resume logic

#### UploadProgress
Progress visualization component:
- Overall progress bar
- Chunk status grid
- Upload statistics (speed, ETA)
- Failed chunk warnings

### Services

#### api.js
API client for backend communication:
- `initUpload()` - Initialize upload session
- `uploadChunk()` - Upload single chunk
- `getUploadStatus()` - Get upload status
- `completeUpload()` - Complete upload

#### uploadService.js
High-level upload service:
- `uploadFile()` - Complete upload flow
- `retryFailedChunks()` - Retry failed chunks
- Parallel upload management
- Retry logic with exponential backoff

### Utils

#### chunkManager.js
Chunk management utilities:
- `splitFile()` - Split file into chunks
- `ChunkState` - State tracking class
- LocalStorage persistence helpers

## Configuration

Create `.env` file:

```env
VITE_API_URL=http://localhost:8000
```

## Usage Example

```jsx
import FileUploader from './components/FileUploader';

function App() {
  return <FileUploader />;
}
```

## Upload Flow

1. **File Selection**
   - User selects file via drag-and-drop or file input
   - File metadata displayed (name, size)

2. **Initialization**
   - Frontend calls `POST /api/upload/init`
   - Receives `uploadId` and `chunkSize`
   - File split into chunks

3. **Resume Check**
   - Frontend calls `GET /api/upload/status/{uploadId}`
   - Merges server state with local state
   - Identifies missing chunks

4. **Parallel Upload**
   - Uploads missing chunks in parallel (5 concurrent)
   - Tracks progress per chunk
   - Retries failed chunks with exponential backoff

5. **Completion**
   - When all chunks uploaded, calls `POST /api/upload/complete/{uploadId}`
   - Displays success message with file metadata
   - Cleans up local state

## Resume Logic

### Server State
- On initialization, check server for existing chunks
- Merge server state with local state
- Only upload missing chunks

### Local Storage (Optional)
- Save upload state to localStorage
- Restore state on page reload
- Clear on successful completion

### Retry Logic
- Failed chunks marked for retry
- Exponential backoff: 1s, 2s, 4s
- Max 3 retries per chunk
- Manual retry button for failed chunks

## Error Handling

### Network Errors
- Automatic retry with exponential backoff
- Failed chunks marked for manual retry
- Error messages displayed to user

### Server Errors
- 400: Invalid request (display error message)
- 404: Upload session not found (start new upload)
- 500: Server error (retry or contact support)

## Performance

### Chunk Size
- Default: 1MB per chunk
- Configurable via backend
- Balance between network efficiency and resume granularity

### Concurrency
- Default: 5 concurrent uploads
- Configurable in `uploadService.js`
- Prevents overwhelming server

### Progress Updates
- Real-time chunk status updates
- Throttled progress bar updates
- Efficient state management

## Production Considerations

### Build Optimization
```bash
npm run build
```
- Minified and optimized bundle
- Code splitting
- Asset optimization

### Environment Variables
- Use different API URLs for dev/staging/prod
- Configure via `.env` files
- Never commit sensitive data

### Error Tracking
- Integrate Sentry or similar
- Log errors to monitoring service
- User-friendly error messages

### Accessibility
- Keyboard navigation support
- Screen reader compatibility
- ARIA labels on interactive elements

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Development

### Hot Reload
Vite provides instant HMR (Hot Module Replacement) for fast development.

### Linting
```bash
# Add ESLint if needed
npm install -D eslint
```

### Testing
```bash
# Add testing framework
npm install -D vitest @testing-library/react
```

## Troubleshooting

### Upload Fails Immediately
- Check backend is running on port 8000
- Verify CORS configuration
- Check browser console for errors

### Resume Not Working
- Verify server state endpoint is working
- Check localStorage is enabled
- Verify uploadId is persisted

### Slow Uploads
- Check network connection
- Reduce concurrency if server is overwhelmed
- Increase chunk size (if supported by backend)

