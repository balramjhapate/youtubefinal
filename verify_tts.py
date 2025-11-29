import sys
import os
import re
import logging
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append('/Volumes/Data/WebSites/youtubefinal')

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_clean_script():
    print("\n--- Testing Script Cleaning ---")
    from legacy.root_debris.downloader.utils import get_clean_script_for_tts
    
    sample_script = """**शीर्षक:** डरावनी कहानी
**आवाज़:** नरेटर

00:00:05 क्या आपने कभी सोचा है कि अंधेरे में क्या होता है?
[Visual: Dark forest]
(Sound of wind)
ठीक है, मैं समझ गया। यहाँ स्क्रिप्ट है:

एक बार की बात है... [short pause] एक जंगल था।
वहाँ एक राक्षस रहता था। [scared]

subscribe और like करना न भूलें!
"""
    
    clean = get_clean_script_for_tts(sample_script)
    print(f"Original:\n{sample_script}")
    print(f"Cleaned:\n{clean}")
    
    assert "शीर्षक" not in clean
    assert "00:00:05" not in clean
    assert "Visual:" not in clean
    assert "Sound of wind" not in clean
    assert "ठीक है" not in clean
    assert "subscribe" not in clean
    assert "एक बार की बात है" in clean
    assert "[short pause]" in clean
    assert "[scared]" in clean
    print("✅ Script cleaning passed!")

def test_tts_speed_calculation():
    print("\n--- Testing TTS Speed Calculation ---")
    from legacy.root_debris.downloader.gemini_tts_service import GeminiTTSService
    
    service = GeminiTTSService(api_key="test_key")
    
    # Mock requests.post
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Fix mock structure to include mimeType
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{
                        'inlineData': {
                            'data': 'UklGRi4AAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQcAAAAAAA==', # Valid base64 WAV header
                            'mimeType': 'audio/mp3'
                        }
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        # Test Case 1: Normal Speed
        text = "This is a test sentence with about ten words for calculation."
        service.generate_speech(text, video_duration=4.0) # ~2.5 words/sec -> 4s
        
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        prompt = payload['contents'][0]['parts'][0]['text']
        print(f"Prompt for Normal Speed:\n{prompt}")
        assert "natural, moderate pace" in prompt or "slightly" in prompt
        
        # Test Case 2: Fast Speed needed
        # 10 words -> est 4s. If video is 2s -> need 2x speed
        service.generate_speech(text, video_duration=2.0)
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        prompt = payload['contents'][0]['parts'][0]['text']
        print(f"Prompt for Fast Speed:\n{prompt}")
        assert "fast pace" in prompt
        
        # Test Case 3: Slow Speed needed
        # 10 words -> est 4s. If video is 8s -> need 0.5x speed
        service.generate_speech(text, video_duration=8.0)
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        prompt = payload['contents'][0]['parts'][0]['text']
        print(f"Prompt for Slow Speed:\n{prompt}")
        assert "slow" in prompt or "relaxed" in prompt

    print("✅ TTS Speed Calculation passed!")

def debug_regex():
    print("\n--- Debugging Regex ---")
    import re
    line = "subscribe और like करना न भूलें!"
    pattern = r'subscribe\s+और\s+like'
    match = re.search(pattern, line, re.IGNORECASE)
    print(f"Line: '{line}'")
    print(f"Pattern: '{pattern}'")
    print(f"Match: {match}")

if __name__ == "__main__":
    try:
        debug_regex()
        test_clean_script()
        test_tts_speed_calculation()
        print("\n🎉 All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
