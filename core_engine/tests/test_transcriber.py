import pytest
from unittest.mock import MagicMock, patch
import os
from engine.transcriber import Transcriber

@pytest.fixture
def mock_whisper():
    with patch('whisper.load_model') as mock_load:
        model = mock_load.return_value
        model.transcribe.return_value = {
            'segments': [
                {'start': 0.0, 'end': 2.0, 'text': 'Hello world'}
            ]
        }
        yield mock_load

def test_transcriber_init(mock_whisper):
    with patch('subprocess.run') as mock_run:
        transcriber = Transcriber(model_size="tiny")
        assert mock_whisper.called

def test_transcription_logic(mock_whisper):
    with patch('subprocess.run') as mock_run, \
         patch('os.remove') as mock_remove, \
         patch('os.path.exists', return_value=True):
        
        transcriber = Transcriber(model_size="tiny")
        result = transcriber.process_video("dummy.mp4")
        
        assert len(result) == 1
        assert result[0]['text'] == 'Hello world'
        assert mock_run.called
