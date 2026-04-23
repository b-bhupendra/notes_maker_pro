import pytest
from unittest.mock import MagicMock, patch
import json
import os
from engine.analyzer import KBConverter

@pytest.fixture
def mock_dependencies():
    with patch('engine.analyzer.ocr.OCRProcessor.extract_text') as mock_ocr, \
         patch('engine.analyzer.llm.LLMProcessor.analyze_moment') as mock_llm:
        
        mock_ocr.return_value = "Sample OCR Text"
        mock_llm.return_value = {
            "total_description": "A test description",
            "key_takeaways": ["Point 1", "Point 2"]
        }
        yield mock_ocr, mock_llm

def test_kb_converter_processing(mock_dependencies, tmp_path):
    mock_ocr, mock_llm = mock_dependencies
    
    # Create a dummy metadata.json
    metadata = {
        "synchronized": [
            {
                "timestamp": 10.0,
                "frame_path": "frames/frame_10.jpg",
                "text": "Hello world"
            }
        ]
    }
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata))
    
    converter = KBConverter()
    output_path = tmp_path / "kb.json"
    result = converter.process_metadata(str(metadata_path), str(output_path))
    
    assert len(result) == 1
    assert result[0]['ocr_text'] == "Sample OCR Text"
    assert result[0]['visual_description'] == "A test description"
    assert os.path.exists(str(output_path))
    
    with open(output_path, "r") as f:
        saved_data = json.load(f)
        assert saved_data[0]['timeframe'] == 10.0
