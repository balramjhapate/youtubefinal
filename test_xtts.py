#!/usr/bin/env python3
import os
import sys
import django
import traceback

# Setup Django
sys.path.insert(0, '/home/radha/Downloads/narendras/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rednote_project.settings')
django.setup()

from downloader.models import SavedVoice
from downloader.xtts_views import get_tts_model

print("Testing XTTS model loading...")
try:
    model = get_tts_model()
    print("✓ TTS model loaded successfully!")
    
    # Get first voice
    voice = SavedVoice.objects.first()
    if voice:
        print(f"\nTesting speech generation with voice: {voice.name}")
        print(f"Voice file: {voice.file.path}")
        
        # Test generation
        output_path = "/tmp/test_xtts_output.wav"
        model.tts_to_file(
            text="Hello, this is a test.",
            speaker_wav=voice.file.path,
            language="en",
            file_path=output_path
        )
        
        if os.path.exists(output_path):
            print(f"✓ Audio generated successfully: {output_path}")
            print(f"  File size: {os.path.getsize(output_path)} bytes")
        else:
            print("✗ Audio file was not created")
    else:
        print("No voices found to test with")
        
except Exception as e:
    print(f"\n✗ Error: {str(e)}")
    print("\nFull traceback:")
    traceback.print_exc()
