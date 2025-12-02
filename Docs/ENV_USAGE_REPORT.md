# Environment Variables (.env) Usage Report

## Summary

This project **does not use a `.env` file** for loading environment variables. Instead, it relies on:

-   **Backend (Django)**: Direct `os.environ.get()` calls with default values
-   **Frontend (Vite)**: Vite's built-in environment variable support via `import.meta.env`

## Current Status

### ✅ `.env` File Status

-   `.env` is listed in `.gitignore` (line 25) - **correctly ignored**
-   **No `.env` file exists** in the repository
-   **No `.env.example` file exists** for documentation

### ⚠️ Missing `.env` Support

-   **No `python-dotenv` package** in `requirements.txt`
-   **No `load_dotenv()` calls** in Django settings
-   Environment variables must be set via system environment or shell exports

## Backend Environment Variables (Django)

All environment variables are read using `os.environ.get()` in `backend/settings.py`:

### NCA Toolkit API Configuration

| Variable          | Default                   | Description                                         |
| ----------------- | ------------------------- | --------------------------------------------------- |
| `NCA_API_URL`     | `'http://localhost:8080'` | Base URL of NCA Toolkit API                         |
| `NCA_API_KEY`     | `'my_secret_key_123'`     | API key for authentication                          |
| `NCA_API_TIMEOUT` | `'600'`                   | Request timeout in seconds (10 minutes)             |
| `NCA_API_ENABLED` | `'false'`                 | Enable/disable NCA API (must be `'true'` to enable) |

### Whisper Transcription Configuration

| Variable                          | Default    | Description                                      |
| --------------------------------- | ---------- | ------------------------------------------------ |
| `WHISPER_MODEL_SIZE`              | `'medium'` | Model size: tiny, base, small, medium, large     |
| `WHISPER_DEVICE`                  | `'cpu'`    | Device: 'cpu' or 'cuda' (GPU)                    |
| `WHISPER_CONFIDENCE_THRESHOLD`    | `'-1.5'`   | Confidence threshold for retry                   |
| `WHISPER_RETRY_WITH_LARGER_MODEL` | `'true'`   | Auto-retry low confidence segments               |
| `WHISPERX_ENABLED`                | `'false'`  | Enable WhisperX for better alignment/diarization |

### Dual Transcription Mode

| Variable                     | Default  | Description                             |
| ---------------------------- | -------- | --------------------------------------- |
| `DUAL_TRANSCRIPTION_ENABLED` | `'true'` | Run both NCA and Whisper for comparison |

### Code Location

```python
# backend/settings.py (lines 156-182)
NCA_API_URL = os.environ.get('NCA_API_URL', 'http://localhost:8080')
NCA_API_KEY = os.environ.get('NCA_API_KEY', 'my_secret_key_123')
NCA_API_TIMEOUT = int(os.environ.get('NCA_API_TIMEOUT', '600'))
NCA_API_ENABLED = os.environ.get('NCA_API_ENABLED', 'false').lower() == 'true'
WHISPER_MODEL_SIZE = os.environ.get('WHISPER_MODEL_SIZE', 'medium')
WHISPER_DEVICE = os.environ.get('WHISPER_DEVICE', 'cpu')
WHISPER_CONFIDENCE_THRESHOLD = float(os.environ.get('WHISPER_CONFIDENCE_THRESHOLD', '-1.5'))
WHISPER_RETRY_WITH_LARGER_MODEL = os.environ.get('WHISPER_RETRY_WITH_LARGER_MODEL', 'true').lower() == 'true'
WHISPERX_ENABLED = os.environ.get('WHISPERX_ENABLED', 'false').lower() == 'true'
DUAL_TRANSCRIPTION_ENABLED = os.environ.get('DUAL_TRANSCRIPTION_ENABLED', 'true').lower() == 'true'
```

## Frontend Environment Variables (Vite/React)

### Current Usage

| Variable       | Default  | Description           | Location                                |
| -------------- | -------- | --------------------- | --------------------------------------- |
| `VITE_API_URL` | `'/api'` | API base URL          | `frontend/src/api/client.js:4`          |
| `DEV`          | (auto)   | Development mode flag | `frontend/src/hooks/useWebSocket.js:28` |

### Code Location

```javascript
// frontend/src/api/client.js (line 4)
const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

// frontend/src/hooks/useWebSocket.js (line 28)
const isDev = import.meta.env.DEV;
```

### How Vite Environment Variables Work

-   Vite automatically loads `.env` files from the project root
-   Variables must be prefixed with `VITE_` to be exposed to client code
-   Files are loaded in this order:
    1. `.env` (loaded in all cases)
    2. `.env.local` (loaded in all cases, ignored by git)
    3. `.env.[mode]` (e.g., `.env.development`)
    4. `.env.[mode].local` (e.g., `.env.development.local`)

## How to Set Environment Variables

### Option 1: System Environment Variables (Current Method)

```bash
# Set before running Django
export NCA_API_URL="http://localhost:8080"
export NCA_API_KEY="your_api_key_here"
export NCA_API_ENABLED="true"

# Run Django
python manage.py runserver
```

### Option 2: Shell Script (run_project.sh)

The `run_project.sh` script doesn't currently load a `.env` file, but you could add:

```bash
# Add to run_project.sh before starting Django
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
fi
```

### Option 3: Add python-dotenv Support (Recommended)

To enable `.env` file support in Django:

1. **Add to `backend/requirements.txt`:**

    ```
    python-dotenv>=1.0.0
    ```

2. **Add to `backend/settings.py` (at the top, after imports):**

    ```python
    from dotenv import load_dotenv
    import os

    # Load environment variables from .env file
    load_dotenv()
    ```

3. **Create `.env.example` file:**

    ```bash
    # NCA Toolkit API Configuration
    NCA_API_URL=http://localhost:8080
    NCA_API_KEY=my_secret_key_123
    NCA_API_TIMEOUT=600
    NCA_API_ENABLED=false

    # Whisper Configuration
    WHISPER_MODEL_SIZE=medium
    WHISPER_DEVICE=cpu
    WHISPER_CONFIDENCE_THRESHOLD=-1.5
    WHISPER_RETRY_WITH_LARGER_MODEL=true
    WHISPERX_ENABLED=false

    # Dual Transcription
    DUAL_TRANSCRIPTION_ENABLED=true
    ```

4. **Create `.env` file** (copy from `.env.example` and customize)

## Recommendations

### ✅ What's Working Well

1. All environment variables have sensible defaults
2. `.env` is properly ignored in `.gitignore`
3. Frontend uses Vite's built-in environment variable support

### ⚠️ Improvements Needed

1. **Add `python-dotenv` support** for easier local development
2. **Create `.env.example`** file for documentation
3. **Document environment variables** in README or setup guide
4. **Consider adding `.env.local`** to `.gitignore` (already covered by `.env` pattern)

### 🔒 Security Notes

-   **Never commit `.env` files** to version control (already in `.gitignore` ✅)
-   **Use `.env.example`** to document required variables without exposing secrets
-   **In production**, use proper secret management (AWS Secrets Manager, Kubernetes secrets, etc.)

## Files That Reference Environment Variables

### Backend

-   `backend/settings.py` - All Django environment variable usage

### Frontend

-   `frontend/src/api/client.js` - `VITE_API_URL`
-   `frontend/src/hooks/useWebSocket.js` - `import.meta.env.DEV`

### Documentation

-   `Docs/NCA_RUN_GUIDE.md` - Documents NCA API environment variables
-   `Docs/INTEGRATION_SUMMARY.md` - Mentions environment variable setup

### Scripts

-   `run_project.sh` - Starts services but doesn't load `.env` file

## Conclusion

The project currently **does not use `.env` files** but relies on system environment variables. All variables have defaults, so the project works without any environment setup. However, adding `python-dotenv` support would make local development easier and more consistent with common Django practices.
