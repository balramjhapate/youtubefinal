# TTS Installation Guide - Coqui TTS (XTTS v2)

## ⚠️ CRITICAL: Python Version Requirement

**Coqui TTS ONLY works with Python 3.9, 3.10, or 3.11**
**It does NOT work with Python 3.12 or higher!**

## Check Your Python Version

```bash
python3 --version
```

If you have Python 3.12+, you need to install Python 3.11 or 3.10.

---

## Installation Steps

### Option 1: Install in Current Environment (if Python 3.9-3.11)

```bash
# Navigate to your project
cd /Volumes/Data/WebSites/youtubefinal/backend

# Install Coqui TTS
pip3 install TTS

# Or if using requirements.txt
pip3 install -r requirements.txt
```

### Option 2: Create Virtual Environment with Python 3.11

If you have Python 3.12+, you need to create a virtual environment with Python 3.11:

#### Step 1: Install Python 3.11 (if not installed)

**On macOS (using Homebrew):**
```bash
brew install python@3.11
```

**On Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv
```

#### Step 2: Create Virtual Environment

```bash
# Navigate to project root
cd /Volumes/Data/WebSites/youtubefinal/backend

# Create virtual environment with Python 3.11
python3.11 -m venv venv_tts

# Activate virtual environment
source venv_tts/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install TTS
pip install TTS

# Install other project dependencies
pip install -r requirements.txt
```

#### Step 3: Always Activate Virtual Environment Before Running

```bash
cd /Volumes/Data/WebSites/youtubefinal/backend
source venv_tts/bin/activate
python manage.py runserver
```

---

## Verify Installation

After installing, verify TTS is working:

```bash
cd /Volumes/Data/WebSites/youtubefinal/backend

python3 manage.py shell -c "from downloader.xtts_service import TTS_AVAILABLE; print(f'TTS Available: {TTS_AVAILABLE}')"
```

**Expected output:**
```
TTS Available: True
```

If you see `TTS Available: False`, check the error message for details.

---

## Common Installation Issues

### Issue 1: "No module named 'TTS'"

**Solution:** TTS is not installed. Run:
```bash
pip3 install TTS
```

### Issue 2: "Python version not supported"

**Solution:** You're using Python 3.12+. Install Python 3.11 and create a virtual environment (see Option 2 above).

### Issue 3: "ImportError: cannot import name 'packaging'"

**Solution:**
```bash
pip3 install packaging
```

### Issue 4: "torch not found"

**Solution:** TTS requires PyTorch. Install it:
```bash
# For CPU only
pip3 install torch torchvision torchaudio

# For GPU (CUDA)
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Issue 5: "XTTS model download fails"

**Solution:** The model will download automatically on first use. Ensure you have:
- Internet connection
- ~2GB free disk space
- Patience (first download takes 5-10 minutes)

---

## Test TTS Manually

Once installed, test TTS generation:

```bash
cd /Volumes/Data/WebSites/youtubefinal/backend

python3 manage.py shell
```

Then in the Python shell:

```python
from downloader.xtts_service import XTTSService, TTS_AVAILABLE

if TTS_AVAILABLE:
    print("✓ TTS is available!")
    service = XTTSService()
    print("✓ Service created!")
    print("✓ Model will load on first use")
else:
    print("✗ TTS is NOT available")
```

---

## After Installation

Once TTS is installed:

1. **Restart Django server:**
   ```bash
   # Stop the server (Ctrl+C)
   # Start it again
   python3 manage.py runserver
   ```

2. **Process a video:**
   - Go to Videos page
   - Click on a video
   - Click "Process Video"
   - TTS should now work!

3. **Check for errors:**
   - If TTS still fails, check the Django console for error messages
   - The error will now show: "TTS service not available. Please install Coqui TTS..."

---

## System Requirements

- **Python:** 3.9, 3.10, or 3.11 (NOT 3.12+)
- **RAM:** 4GB minimum, 8GB recommended
- **Disk Space:** 2GB for model files
- **GPU:** Optional (CUDA-enabled GPU speeds up processing)

---

## Alternative: Use Pre-recorded Audio

If you can't install TTS, you can:

1. Generate audio externally (using online TTS services)
2. Upload the audio file manually
3. Use the video processing without TTS

---

## Need Help?

If you're still having issues:

1. Check Python version: `python3 --version`
2. Check TTS installation: `pip3 list | grep TTS`
3. Check error logs in Django console
4. Share the error message for further assistance

---

## Quick Reference

```bash
# Check Python version
python3 --version

# Install TTS
pip3 install TTS

# Verify installation
python3 -c "from TTS.api import TTS; print('TTS OK')"

# Check in Django
cd /Volumes/Data/WebSites/youtubefinal/backend
python3 manage.py shell -c "from downloader.xtts_service import TTS_AVAILABLE; print(TTS_AVAILABLE)"
```

---

## Success Indicators

✅ `TTS Available: True` in shell command
✅ No import errors when starting Django
✅ "Process Video" completes without TTS errors
✅ Synthesized audio file is generated
✅ Final video has Hindi audio

🎉 **You're all set!**
