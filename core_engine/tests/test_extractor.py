import pytest
from unittest.mock import MagicMock, patch
import os
from engine.extractor import FrameExtractor

@pytest.fixture
def mock_cv2():
    with patch('cv2.VideoCapture') as mock_cap, \
         patch('cv2.imwrite') as mock_write, \
         patch('cv2.resize') as mock_resize:
        
        # Mock instance
        instance = mock_cap.return_value
        instance.isOpened.return_value = True
        instance.get.side_effect = lambda prop: {
            0: 1000, # CAP_PROP_POS_MSEC (not used)
            1: 0,    # CAP_PROP_POS_FRAMES
            5: 30,   # CAP_PROP_FPS
            7: 300   # CAP_PROP_FRAME_COUNT
        }.get(prop, 0)
        instance.read.return_value = (True, MagicMock(shape=(1080, 1920, 3)))
        
        yield {
            'cap': mock_cap,
            'write': mock_write,
            'resize': mock_resize
        }

def test_extractor_init(mock_cv2):
    extractor = FrameExtractor("dummy.mp4", output_dir="test_screenshots")
    assert extractor.total_frames == 300
    assert extractor.fps == 30
    assert extractor.duration == 10.0

def test_extract_n_frames(mock_cv2):
    extractor = FrameExtractor("dummy.mp4", output_dir="test_screenshots")
    frames = extractor.extract_n_frames(2)
    
    assert len(frames) == 2
    assert mock_cv2['write'].call_count == 2
    # Verify resizing was called for 1080p -> 720p
    assert mock_cv2['resize'].called

def test_extract_at_timestamps(mock_cv2):
    extractor = FrameExtractor("dummy.mp4", output_dir="test_screenshots")
    frames = extractor.extract_at_timestamps([1.0, 5.0])
    
    assert len(frames) == 2
    assert frames[0]['timestamp'] == 1.0
