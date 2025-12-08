"""
AI-specific integration hooks for validation, metadata generation, and security scanning.

This module provides placeholders and integration points for:
- Dataset/artifact validation
- Metadata generation for data catalog
- Security scanning (virus, PII detection)
- Downstream pipeline integration (fine-tuning, data curation)
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timezone

from .models import FileMetadata


class AIIntegration:
    """AI-specific integration hooks and utilities."""
    
    def __init__(self, metadata_store_path: str = None):
        """
        Initialize AI integration.
        
        Args:
            metadata_store_path: Path to JSON file for storing metadata
        """
        if metadata_store_path is None:
            # Default to backend directory
            backend_dir = Path(__file__).parent.parent
            metadata_store_path = backend_dir / "metadata_store.json"
        self.metadata_store_path = Path(metadata_store_path)
        self._ensure_metadata_store()
    
    def _ensure_metadata_store(self):
        """Ensure metadata store file exists."""
        if not self.metadata_store_path.exists():
            with open(self.metadata_store_path, 'w') as f:
                json.dump({"uploads": []}, f)
    
    def validate_dataset(self, filepath: Path, file_type: str) -> tuple[bool, Optional[str]]:
        """
        Validate dataset format and schema.
        
        This is a placeholder for actual validation logic. In production, you would:
        - Check JSONL format (one JSON object per line)
        - Validate CSV structure and required columns
        - Verify Parquet schema
        - Check for required fields in training data
        
        Args:
            filepath: Path to the uploaded file
            file_type: Detected file type (dataset, model_artifact, etc.)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if file_type != 'dataset':
            return True, None  # Skip validation for non-dataset files
        
        try:
            # Placeholder: Check file extension
            ext = filepath.suffix.lower()
            valid_extensions = {'.jsonl', '.json', '.csv', '.parquet', '.tsv', '.txt'}
            
            if ext not in valid_extensions:
                return False, f"Invalid dataset format: {ext}. Expected one of {valid_extensions}"
            
            # Placeholder: Basic file structure check
            if ext == '.jsonl':
                # Check if file is valid JSONL (one JSON object per line)
                with open(filepath, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if i >= 10:  # Check first 10 lines
                            break
                        try:
                            json.loads(line.strip())
                        except json.JSONDecodeError:
                            return False, f"Invalid JSONL format at line {i+1}"
            
            return True, None
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def validate_schema(self, filepath: Path, file_type: str) -> tuple[bool, Optional[str]]:
        """
        Validate data schema for datasets.
        
        Placeholder for schema validation. In production, you would:
        - Check for required fields (e.g., 'text', 'label' for classification)
        - Validate data types
        - Check for missing values
        - Verify label distributions
        
        Args:
            filepath: Path to the uploaded file
            file_type: Detected file type
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if file_type != 'dataset':
            return True, None
        
        # Placeholder: In production, implement actual schema validation
        # For example, for a fine-tuning dataset, check for 'messages' or 'prompt' fields
        return True, None
    
    def generate_metadata(self, filepath: Path, upload_id: str, metadata: FileMetadata) -> Dict:
        """
        Generate comprehensive metadata for data catalog and lineage tracking.
        
        Args:
            filepath: Path to the completed file
            upload_id: Upload session identifier
            metadata: Basic file metadata
            
        Returns:
            Enhanced metadata dictionary
        """
        enhanced_metadata = {
            "uploadId": upload_id,
            "filename": metadata.filename,
            "size": metadata.size,
            "checksum": metadata.checksum,
            "timestamp": metadata.timestamp,
            "fileType": metadata.fileType,
            "filepath": metadata.filepath,
            "lineage": {
                "source": "user_upload",
                "upload_timestamp": metadata.timestamp,
                "downstream_jobs": []
            }
        }
        
        # Add file-specific metadata
        if metadata.fileType == 'dataset':
            enhanced_metadata["dataset_info"] = {
                "format": filepath.suffix.lower(),
                "estimated_records": self._estimate_record_count(filepath),
                "preview_available": True
            }
        elif metadata.fileType == 'model_artifact':
            enhanced_metadata["model_info"] = {
                "format": filepath.suffix.lower(),
                "framework": self._detect_model_framework(filepath)
            }
        
        return enhanced_metadata
    
    def _estimate_record_count(self, filepath: Path) -> Optional[int]:
        """Estimate number of records in a dataset file."""
        try:
            ext = filepath.suffix.lower()
            if ext == '.jsonl':
                # Count lines (one record per line)
                with open(filepath, 'rb') as f:
                    return sum(1 for _ in f)
            elif ext == '.csv':
                # Count lines minus header
                with open(filepath, 'rb') as f:
                    return max(0, sum(1 for _ in f) - 1)
            return None
        except Exception:
            return None
    
    def _detect_model_framework(self, filepath: Path) -> str:
        """Detect ML framework from file extension."""
        ext = filepath.suffix.lower()
        framework_map = {
            '.pt': 'pytorch',
            '.pth': 'pytorch',
            '.ckpt': 'pytorch',
            '.safetensors': 'safetensors',
            '.onnx': 'onnx',
            '.pb': 'tensorflow',
            '.h5': 'keras'
        }
        return framework_map.get(ext, 'unknown')
    
    def scan_file(self, filepath: Path) -> tuple[bool, Optional[str], Dict]:
        """
        Security scanning: virus and PII detection.
        
        Placeholder for security scanning. In production, you would:
        - Integrate ClamAV or cloud-based virus scanner
        - Use PII detection libraries (e.g., presidio, spaCy)
        - Scan for sensitive patterns (SSN, credit cards, etc.)
        - Check for malicious content
        
        Args:
            filepath: Path to the file to scan
            
        Returns:
            Tuple of (is_safe, error_message, scan_results)
        """
        scan_results = {
            "virus_scan": {
                "status": "skipped",
                "message": "Virus scanning not implemented (placeholder)"
            },
            "pii_detection": {
                "status": "skipped",
                "message": "PII detection not implemented (placeholder)",
                "detected_pii": []
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Placeholder: In production, implement actual scanning
        # Example:
        # virus_result = self._scan_virus(filepath)
        # pii_result = self._detect_pii(filepath)
        # if virus_result.has_virus or pii_result.has_pii:
        #     return False, "Security scan failed", scan_results
        
        return True, None, scan_results
    
    def register_dataset(self, upload_id: str, metadata: Dict) -> str:
        """
        Register dataset in dataset registry.
        
        Args:
            upload_id: Upload session identifier
            metadata: File metadata
            
        Returns:
            Dataset registry ID
        """
        # Load existing metadata store
        with open(self.metadata_store_path, 'r') as f:
            store = json.load(f)
        
        # Add new entry
        entry = {
            "id": upload_id,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            **metadata
        }
        store["uploads"].append(entry)
        
        # Save metadata store
        with open(self.metadata_store_path, 'w') as f:
            json.dump(store, f, indent=2)
        
        return upload_id
    
    def notify_fine_tuning_pipeline(self, filepath: Path, metadata: Dict) -> Optional[str]:
        """
        Trigger fine-tuning pipeline job.
        
        Placeholder for pipeline integration. In production, you would:
        - Add job to Celery/RQ queue
        - Send webhook to pipeline service
        - Create Kubernetes job
        - Trigger AWS Batch / Google Cloud Run job
        
        Args:
            filepath: Path to the uploaded file
            metadata: File metadata
            
        Returns:
            Job ID if job was created, None otherwise
        """
        # Placeholder: In production, implement actual job creation
        # Example:
        # job = fine_tuning_queue.enqueue(
        #     process_fine_tuning_dataset,
        #     filepath=str(filepath),
        #     metadata=metadata
        # )
        # return job.id
        
        print(f"[PLACEHOLDER] Would trigger fine-tuning pipeline for: {filepath}")
        print(f"[PLACEHOLDER] Metadata: {json.dumps(metadata, indent=2)}")
        return None
    
    def notify_data_curation_system(self, filepath: Path, metadata: Dict) -> Optional[str]:
        """
        Trigger data curation or labeling system.
        
        Placeholder for data curation integration. In production, you would:
        - Register dataset in labeling platform (Labelbox, Scale, etc.)
        - Trigger data quality checks
        - Start data validation pipeline
        
        Args:
            filepath: Path to the uploaded file
            metadata: File metadata
            
        Returns:
            Curation job ID if created, None otherwise
        """
        # Placeholder: In production, implement actual integration
        print(f"[PLACEHOLDER] Would trigger data curation for: {filepath}")
        return None
    
    def get_lineage(self, upload_id: str) -> Optional[Dict]:
        """Get lineage information for an upload."""
        with open(self.metadata_store_path, 'r') as f:
            store = json.load(f)
        
        for entry in store["uploads"]:
            if entry.get("id") == upload_id:
                return entry.get("lineage", {})
        return None

