#!/bin/bash

# TTS Installation Script for YouTubeFinal Project
# This script installs Coqui TTS and its dependencies

set -e  # Exit on error

echo "========================================="
echo "TTS Installation Script"
echo "========================================="
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Extract major and minor version
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 9 ] && [ "$PYTHON_MINOR" -le 11 ]; then
    echo "✓ Python version is compatible ($PYTHON_VERSION)"
else
    echo "✗ ERROR: Python $PYTHON_VERSION is not compatible!"
    echo "  TTS requires Python 3.9, 3.10, or 3.11"
    echo "  Please install Python 3.11 and create a virtual environment"
    echo "  See TTS_INSTALLATION_GUIDE.md for instructions"
    exit 1
fi

echo ""
echo "Installing Coqui TTS..."
echo "This may take a few minutes..."
echo ""

# Install TTS
pip3 install --upgrade pip
pip3 install TTS
# Fix for Python 3.9 compatibility (bangla package issue)
pip3 install bangla==0.0.2

echo ""
echo "========================================="
echo "Verifying installation..."
echo "========================================="
echo ""

# Navigate to Django project
cd /Volumes/Data/WebSites/youtubefinal/backend

# Verify TTS is available
python3 manage.py shell -c "from downloader.xtts_service import TTS_AVAILABLE; print(f'TTS Available: {TTS_AVAILABLE}')"

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Restart your Django server"
echo "2. Upload a voice sample in Voice Cloning section"
echo "3. Process a video to test TTS"
echo ""
echo "If you see 'TTS Available: True' above, you're all set!"
echo ""
