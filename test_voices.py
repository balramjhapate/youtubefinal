#!/usr/bin/env python3
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/home/radha/Downloads/narendras/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rednote_project.settings')
django.setup()

from downloader.models import SavedVoice

# Check if there are any saved voices
voices = SavedVoice.objects.all()
print(f"Found {voices.count()} saved voices:")
for voice in voices:
    print(f"  - {voice.name}: {voice.file.path if voice.file else 'No file'}")
    if voice.file and os.path.exists(voice.file.path):
        print(f"    File exists: {voice.file.path}")
    else:
        print(f"    File MISSING!")

if voices.count() == 0:
    print("\nNo saved voices found. You need to upload a voice sample first!")
    print("Go to Voice Cloning page and upload an audio file.")
