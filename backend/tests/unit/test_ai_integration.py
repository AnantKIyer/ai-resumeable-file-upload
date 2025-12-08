"""
Unit tests for ai_integration module.
"""
import pytest
import json
from pathlib import Path

from app.ai_integration import AIIntegration
from app.models import FileMetadata


@pytest.mark.unit
class TestAIIntegration:
    """Test AIIntegration class."""
    
    def test_initialization(self, ai_integration: AIIntegration):
        """Test AI integration initialization."""
        assert ai_integration.metadata_store_path.exists()
    
    def test_validate_dataset_valid_jsonl(self, ai_integration: AIIntegration, temp_dir: Path):
        """Test validating a valid JSONL dataset."""
        jsonl_file = temp_dir / "valid.jsonl"
        jsonl_file.write_text('{"text": "hello", "label": 1}\n{"text": "world", "label": 2}\n')
        
        is_valid, error = ai_integration.validate_dataset(jsonl_file, "dataset")
        assert is_valid is True
        assert error is None
    
    def test_validate_dataset_invalid_jsonl(self, ai_integration: AIIntegration, temp_dir: Path):
        """Test validating an invalid JSONL dataset."""
        jsonl_file = temp_dir / "invalid.jsonl"
        jsonl_file.write_text('{"text": "hello"}\ninvalid json\n')
        
        is_valid, error = ai_integration.validate_dataset(jsonl_file, "dataset")
        assert is_valid is False
        assert error is not None
    
    def test_validate_dataset_invalid_format(self, ai_integration: AIIntegration, temp_dir: Path):
        """Test validating dataset with invalid format."""
        invalid_file = temp_dir / "invalid.xyz"
        invalid_file.write_text("data")
        
        is_valid, error = ai_integration.validate_dataset(invalid_file, "dataset")
        assert is_valid is False
        assert "format" in error.lower()
    
    def test_validate_dataset_non_dataset(self, ai_integration: AIIntegration, temp_dir: Path):
        """Test validating non-dataset file returns valid."""
        model_file = temp_dir / "model.pt"
        model_file.write_bytes(b"model data")
        
        is_valid, error = ai_integration.validate_dataset(model_file, "model_artifact")
        assert is_valid is True
    
    def test_validate_schema(self, ai_integration: AIIntegration, temp_dir: Path):
        """Test schema validation (placeholder)."""
        file = temp_dir / "data.jsonl"
        file.write_text('{"text": "test"}\n')
        
        is_valid, error = ai_integration.validate_schema(file, "dataset")
        assert is_valid is True  # Placeholder always returns True
    
    def test_generate_metadata(self, ai_integration: AIIntegration, temp_dir: Path):
        """Test generating metadata."""
        test_file = temp_dir / "test.jsonl"
        test_file.write_text('{"data": "test"}\n' * 100)
        
        metadata = FileMetadata(
            uploadId="test-123",
            filename="test.jsonl",
            size=test_file.stat().st_size,
            checksum=None,
            timestamp="2024-01-01T00:00:00",
            fileType="dataset",
            filepath=str(test_file)
        )
        
        enhanced = ai_integration.generate_metadata(test_file, "test-123", metadata)
        
        assert enhanced["uploadId"] == "test-123"
        assert enhanced["filename"] == "test.jsonl"
        assert "dataset_info" in enhanced
        assert enhanced["fileType"] == "dataset"
    
    def test_generate_metadata_model(self, ai_integration: AIIntegration, temp_dir: Path):
        """Test generating metadata for model artifact."""
        model_file = temp_dir / "model.pt"
        model_file.write_bytes(b"model data")
        
        metadata = FileMetadata(
            uploadId="test-123",
            filename="model.pt",
            size=model_file.stat().st_size,
            checksum=None,
            timestamp="2024-01-01T00:00:00",
            fileType="model_artifact",
            filepath=str(model_file)
        )
        
        enhanced = ai_integration.generate_metadata(model_file, "test-123", metadata)
        assert "model_info" in enhanced
        assert enhanced["fileType"] == "model_artifact"
    
    def test_scan_file(self, ai_integration: AIIntegration, temp_dir: Path):
        """Test security scanning (placeholder)."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        is_safe, error, results = ai_integration.scan_file(test_file)
        
        assert is_safe is True  # Placeholder always returns safe
        assert error is None
        assert "virus_scan" in results
        assert "pii_detection" in results
    
    def test_register_dataset(self, ai_integration: AIIntegration):
        """Test registering dataset in metadata store."""
        metadata = {
            "uploadId": "test-123",
            "filename": "dataset.jsonl",
            "size": 1000,
            "fileType": "dataset"
        }
        
        dataset_id = ai_integration.register_dataset("test-123", metadata)
        assert dataset_id == "test-123"
        
        # Verify it's in the store
        with open(ai_integration.metadata_store_path, 'r') as f:
            store = json.load(f)
        
        assert len(store["uploads"]) > 0
        assert store["uploads"][-1]["id"] == "test-123"
    
    def test_notify_fine_tuning_pipeline(self, ai_integration: AIIntegration, temp_dir: Path):
        """Test notifying fine-tuning pipeline (placeholder)."""
        test_file = temp_dir / "dataset.jsonl"
        test_file.write_text('{"data": "test"}\n')
        
        metadata = {"filename": "dataset.jsonl", "fileType": "dataset"}
        job_id = ai_integration.notify_fine_tuning_pipeline(test_file, metadata)
        
        # Placeholder returns None
        assert job_id is None
    
    def test_notify_data_curation_system(self, ai_integration: AIIntegration, temp_dir: Path):
        """Test notifying data curation system (placeholder)."""
        test_file = temp_dir / "dataset.jsonl"
        test_file.write_text('{"data": "test"}\n')
        
        metadata = {"filename": "dataset.jsonl"}
        curation_id = ai_integration.notify_data_curation_system(test_file, metadata)
        
        # Placeholder returns None
        assert curation_id is None
    
    def test_get_lineage(self, ai_integration: AIIntegration):
        """Test getting lineage information."""
        # Register a dataset first
        metadata = {
            "uploadId": "lineage-test",
            "filename": "test.jsonl",
            "lineage": {"source": "upload"}
        }
        ai_integration.register_dataset("lineage-test", metadata)
        
        lineage = ai_integration.get_lineage("lineage-test")
        assert lineage is not None
    
    def test_get_lineage_nonexistent(self, ai_integration: AIIntegration):
        """Test getting lineage for non-existent upload."""
        lineage = ai_integration.get_lineage("nonexistent")
        assert lineage is None
