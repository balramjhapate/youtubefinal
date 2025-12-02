# CloudPanel Deployment Plan with Authentication

This document provides a comprehensive plan to deploy your Django + React application to CloudPanel with authentication to prevent unauthorized access.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Preparation](#pre-deployment-preparation)
3. [AI/ML Setup on Server](#aiml-setup-on-server)
4. [CloudPanel Setup](#cloudpanel-setup)
5. [Authentication Implementation](#authentication-implementation)
6. [Production Configuration](#production-configuration)
7. [Database Migration](#database-migration)
8. [Static Files & Media](#static-files--media)
9. [SSL/HTTPS Configuration](#sslhttps-configuration)
10. [Deployment Steps](#deployment-steps)
11. [Post-Deployment Verification](#post-deployment-verification)
12. [Troubleshooting](#troubleshooting)
13. [AI/ML Quick Reference](#aiml-quick-reference)

---

## Prerequisites

### Server Requirements

#### Minimum Requirements (CPU-only, slower processing)
- **OS**: Ubuntu 20.04 LTS or 22.04 LTS (recommended)
- **RAM**: Minimum 8GB (16GB+ recommended for AI/ML processing)
- **Storage**: 100GB+ SSD (200GB+ recommended for video storage and ML models)
- **CPU**: 4+ cores (8+ cores recommended)
- **Network**: Public IP address with ports 80, 443, and 22 open

#### Recommended Requirements (with GPU support)
- **OS**: Ubuntu 22.04 LTS
- **RAM**: 16GB+ (32GB+ for large models)
- **Storage**: 200GB+ NVMe SSD
- **CPU**: 8+ cores
- **GPU**: NVIDIA GPU with CUDA support (optional but highly recommended)
  - Minimum: 4GB VRAM (for Whisper medium model)
  - Recommended: 8GB+ VRAM (for Whisper large model and faster processing)
- **Network**: Public IP address with ports 80, 443, and 22 open

### Software Requirements
- CloudPanel installed on the server
- Python 3.9+ installed
- Node.js 18+ and npm installed
- PostgreSQL (will be installed via CloudPanel)
- Redis (for Channels WebSocket support)
- FFmpeg (for video processing)
- **AI/ML Dependencies** (will be installed):
  - PyTorch (CPU or CUDA version)
  - OpenAI Whisper
  - OpenCV
  - NumPy, SciPy
  - Transformers library
  - TTS libraries

### Domain Setup
- Domain name pointing to your server IP
- DNS A record configured

---

## Pre-Deployment Preparation

### 1. Install System Dependencies for AI/ML

Before deploying, install all system-level dependencies required for AI/ML processing:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install FFmpeg (required for video/audio processing)
sudo apt install -y ffmpeg

# Install system libraries for ML
sudo apt install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libgtk-3-dev \
    libatlas-base-dev \
    python3-dev \
    python3-pip \
    python3-venv

# Install CUDA (if you have NVIDIA GPU - OPTIONAL but recommended)
# Check if GPU is available first:
nvidia-smi

# If GPU is available, install CUDA toolkit:
# Visit: https://developer.nvidia.com/cuda-downloads
# Or use CloudPanel's GPU support if available

# Install Redis (if not installed via CloudPanel)
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 2. Update Project for Production

#### A. Create Production Settings File

Create `backend/settings_production.py`:

```python
"""
Production settings for CloudPanel deployment
"""
from .settings import *
import os
from pathlib import Path

# Security Settings
DEBUG = False
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', SECRET_KEY)
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Database - PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'rednote_db'),
        'USER': os.environ.get('DB_USER', 'rednote_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

# Static Files
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'

# Media Files (served via Nginx in production)
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Redis for Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(os.environ.get('REDIS_HOST', '127.0.0.1'), int(os.environ.get('REDIS_PORT', 6379)))],
        },
    },
}

# CORS - Update with your domain
CORS_ALLOWED_ORIGINS = [
    f"https://{host}" for host in ALLOWED_HOSTS if host
] + [
    f"http://{host}" for host in ALLOWED_HOSTS if host
]

# Security Headers
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory
(BASE_DIR / 'logs').mkdir(exist_ok=True)
```

#### B. Update Requirements

Add to `backend/requirements.txt`:
```
# Production dependencies
psycopg2-binary>=2.9.0
gunicorn>=21.2.0
whitenoise>=6.6.0
djangorestframework-simplejwt>=5.3.0
python-dotenv>=1.0.0

# AI/ML Dependencies (already in requirements.txt, but verify versions)
# PyTorch - Choose based on your system:
# For CPU-only:
torch>=2.0.0
torchaudio>=2.0.0

# For GPU (CUDA 11.8) - Uncomment if you have NVIDIA GPU:
# torch>=2.0.0+cu118 --index-url https://download.pytorch.org/whl/cu118
# torchaudio>=2.0.0+cu118 --index-url https://download.pytorch.org/whl/cu118

# For GPU (CUDA 12.1) - Uncomment if you have NVIDIA GPU:
# torch>=2.0.0+cu121 --index-url https://download.pytorch.org/whl/cu121
# torchaudio>=2.0.0+cu121 --index-url https://download.pytorch.org/whl/cu121

# Whisper and ML libraries
openai-whisper>=20231117
transformers>=4.33.0
librosa>=0.10.0
soundfile>=0.12.0
numpy==1.22.0  # Pinned for compatibility

# Computer Vision
opencv-python>=4.8.0
pytesseract>=0.3.10

# Audio/Video Processing
pydub>=0.25.1
ffmpeg-python>=0.2.0

# TTS (if using local TTS, otherwise uses Gemini API)
TTS>=0.22.0

# Note: The existing requirements.txt already includes most of these,
# but ensure versions are compatible with your server setup
```

#### C. Create Environment File Template

Create `.env.production.example`:
```bash
# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DEBUG=False

# Database
DB_NAME=rednote_db
DB_USER=rednote_user
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Frontend
VITE_API_URL=https://yourdomain.com/api

# AI Provider Settings (REQUIRED for AI processing)
# Get API keys from:
# - OpenAI: https://platform.openai.com/api-keys
# - Anthropic: https://console.anthropic.com/
# - Google Gemini: https://makersuite.google.com/app/apikey
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
GOOGLE_API_KEY=your-google-gemini-api-key-here

# Whisper Configuration (Local Transcription)
WHISPER_MODEL_SIZE=medium
# Options: tiny, base, small, medium, large
# - tiny: Fastest, least accurate (~1GB RAM)
# - base: Good balance (~1GB RAM)
# - small: Better accuracy (~2GB RAM)
# - medium: High accuracy (~5GB RAM) - RECOMMENDED
# - large: Best accuracy (~10GB RAM) - Requires 16GB+ RAM

WHISPER_DEVICE=cpu
# Options: cpu, cuda
# Use 'cuda' if you have NVIDIA GPU installed

WHISPER_CONFIDENCE_THRESHOLD=-1.5
WHISPER_RETRY_WITH_LARGER_MODEL=true
WHISPERX_ENABLED=false

# NCA Toolkit API (Optional - for faster transcription)
# If you have NCA Toolkit API deployed separately:
NCA_API_URL=http://localhost:8080
NCA_API_KEY=your-nca-api-key
NCA_API_ENABLED=false
NCA_API_TIMEOUT=600

# Dual Transcription Mode
DUAL_TRANSCRIPTION_ENABLED=true
```

---

## CloudPanel Setup

### 1. Install CloudPanel

If not already installed:
```bash
curl -fsSL https://installer.cloudpanel.io/ce/install.sh | sudo bash
```

### 2. Access CloudPanel

- Navigate to `https://your-server-ip:8443`
- Complete initial setup
- Create admin account

### 3. Create Site

1. Click **"Sites"** → **"Add Site"**
2. Choose **"Python"** as application type
3. Enter your domain name
4. Select Python version (3.9+)
5. Enable **"SSL"** (Let's Encrypt)
6. Click **"Create"**

### 4. Database Setup

1. Go to **"Databases"** → **"Add Database"**
2. Database Type: **PostgreSQL**
3. Database Name: `rednote_db`
4. Username: `rednote_user`
5. Set a strong password
6. Note down credentials for `.env` file

### 5. Install Redis

1. Go to **"Redis"** → **"Add Redis Instance"**
2. Use default settings
3. Note the connection details

---

## Authentication Implementation

### 1. Install JWT Authentication

The authentication will use Django REST Framework Simple JWT for API authentication and Django's built-in session authentication for the admin panel.

### 2. Update Settings

Add to `backend/settings.py` (and production settings):

```python
# Add to INSTALLED_APPS
'rest_framework_simplejwt',

# Update REST_FRAMEWORK settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # Changed from AllowAny
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    # ... rest of settings
}

# JWT Settings
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}
```

### 3. Create Authentication Views

Create `backend/controller/auth_views.py`:

```python
"""
Authentication views for API
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login endpoint - returns JWT tokens
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    
    if user is None:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if not user.is_active:
        return Response(
            {'error': 'User account is disabled'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        }
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    User registration endpoint
    """
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email', '')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email
    )
    
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        }
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def logout(request):
    """
    Logout endpoint - blacklist refresh token
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Successfully logged out'})
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
```

### 4. Update API URLs

Add to `backend/api_urls.py`:

```python
from django.urls import path
from controller.auth_views import login, register, logout
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', login, name='login'),
    path('auth/register/', register, name='register'),
    path('auth/logout/', logout, name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # ... existing API endpoints
]
```

### 5. Create Public Endpoints (if needed)

For endpoints that should remain public (like health checks), use:

```python
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'ok'})
```

---

## Production Configuration

### 1. Create Gunicorn Configuration

Create `backend/gunicorn_config.py`:

```python
"""
Gunicorn configuration for production
"""
import multiprocessing
import os

# Server socket
bind = f"127.0.0.1:{os.environ.get('GUNICORN_PORT', '8000')}"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'rednote_gunicorn'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = None
certfile = None
```

### 2. Create Systemd Service

Create `/etc/systemd/system/rednote.service`:

```ini
[Unit]
Description=RedNote Django Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/home/cloudpanel/htdocs/yourdomain.com/backend
Environment="PATH=/home/cloudpanel/htdocs/yourdomain.com/backend/venv/bin"
EnvironmentFile=/home/cloudpanel/htdocs/yourdomain.com/backend/.env
ExecStart=/home/cloudpanel/htdocs/yourdomain.com/backend/venv/bin/gunicorn \
    --config gunicorn_config.py \
    wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. Create Nginx Configuration

CloudPanel will generate this, but you may need to customize it. The configuration should:

1. Serve static files
2. Proxy API requests to Gunicorn
3. Serve React frontend
4. Handle WebSocket connections

Example Nginx config (CloudPanel will create this automatically, but you can customize):

```nginx
# Static files
location /static/ {
    alias /home/cloudpanel/htdocs/yourdomain.com/backend/staticfiles/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# Media files
location /media/ {
    alias /home/cloudpanel/htdocs/yourdomain.com/backend/media/;
    expires 7d;
    add_header Cache-Control "public";
}

# API and Django
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_redirect off;
}

# WebSocket
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Django admin
location /admin/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# React frontend
location / {
    root /home/cloudpanel/htdocs/yourdomain.com/frontend/dist;
    try_files $uri $uri/ /index.html;
    expires -1;
    add_header Cache-Control "no-cache, no-store, must-revalidate";
}
```

---

## Database Migration

### 1. Migrate from SQLite to PostgreSQL

```bash
# Export data from SQLite
cd backend
python manage.py dumpdata --exclude auth.permission --exclude contenttypes > data.json

# Update settings to use PostgreSQL
# (Use production settings)

# Create new database
python manage.py migrate

# Load data
python manage.py loaddata data.json
```

---

## Static Files & Media

### 1. Collect Static Files

```bash
cd backend
python manage.py collectstatic --noinput
```

### 2. Set Permissions

```bash
sudo chown -R www-data:www-data /home/cloudpanel/htdocs/yourdomain.com/backend/staticfiles
sudo chown -R www-data:www-data /home/cloudpanel/htdocs/yourdomain.com/backend/media
```

---

## SSL/HTTPS Configuration

CloudPanel handles SSL automatically via Let's Encrypt:

1. Go to your site in CloudPanel
2. Click **"SSL"**
3. Enable **"Let's Encrypt"**
4. Enter your email
5. Click **"Install"**

---

## AI/ML Setup on Server

### 1. Install Python ML Dependencies

After setting up the Python virtual environment, install ML dependencies:

```bash
cd /home/cloudpanel/htdocs/yourdomain.com/backend
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install PyTorch (CPU version - default)
# For CPU-only servers:
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# OR for GPU servers (CUDA 11.8):
# pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# OR for GPU servers (CUDA 12.1):
# pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install other ML dependencies
pip install -r requirements.txt

# Verify PyTorch installation
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')"
```

### 2. Download Whisper Models

Whisper models are downloaded automatically on first use, but you can pre-download them:

```bash
cd /home/cloudpanel/htdocs/yourdomain.com/backend
source venv/bin/activate

# Pre-download Whisper models (recommended)
python -c "import whisper; whisper.load_model('tiny'); whisper.load_model('base'); whisper.load_model('small'); whisper.load_model('medium')"

# For large model (only if you have 16GB+ RAM):
# python -c "import whisper; whisper.load_model('large')"

# Models are stored in: ~/.cache/whisper/
# You can check disk usage:
du -sh ~/.cache/whisper/
```

**Model Sizes:**
- `tiny`: ~39 MB
- `base`: ~74 MB
- `small`: ~244 MB
- `medium`: ~769 MB
- `large`: ~1550 MB

### 3. Configure GPU Support (Optional but Recommended)

If you have an NVIDIA GPU:

```bash
# Check GPU availability
nvidia-smi

# Install CUDA toolkit (if not already installed)
# Follow NVIDIA's installation guide for your Ubuntu version

# Verify PyTorch can see GPU
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')"

# Update .env file
# Set WHISPER_DEVICE=cuda
```

**Performance Improvement with GPU:**
- CPU: ~2x realtime (medium model)
- GPU: ~10-30x realtime (medium model)
- GPU is especially beneficial for large model

### 4. Optimize Memory Usage

For servers with limited RAM, configure model caching:

```bash
# Create a script to manage Whisper model cache
cat > /home/cloudpanel/htdocs/yourdomain.com/backend/manage_whisper_cache.sh << 'EOF'
#!/bin/bash
# Clear old Whisper models if disk space is low
CACHE_DIR="$HOME/.cache/whisper"
MAX_SIZE_GB=5

# Check cache size
CACHE_SIZE=$(du -sm "$CACHE_DIR" 2>/dev/null | cut -f1)
CACHE_SIZE_GB=$((CACHE_SIZE / 1024))

if [ "$CACHE_SIZE_GB" -gt "$MAX_SIZE_GB" ]; then
    echo "Whisper cache is ${CACHE_SIZE_GB}GB, cleaning up..."
    # Keep only medium and base models
    find "$CACHE_DIR" -name "*.pt" ! -name "*medium*" ! -name "*base*" -delete
    echo "Cache cleaned"
fi
EOF

chmod +x /home/cloudpanel/htdocs/yourdomain.com/backend/manage_whisper_cache.sh

# Add to crontab (run weekly)
(crontab -l 2>/dev/null; echo "0 2 * * 0 /home/cloudpanel/htdocs/yourdomain.com/backend/manage_whisper_cache.sh") | crontab -
```

### 5. Set Up AI Provider API Keys

Configure API keys in Django admin or via environment variables:

```bash
# Add to .env file (already done in previous step)
# Then set up in Django admin:
# 1. Go to https://yourdomain.com/admin
# 2. Navigate to AI Provider Settings
# 3. Add your API keys for OpenAI, Anthropic, or Gemini
```

**API Key Setup:**
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/
- **Google Gemini**: https://makersuite.google.com/app/apikey

### 6. Test AI/ML Components

After installation, test the AI/ML setup:

```bash
cd /home/cloudpanel/htdocs/yourdomain.com/backend
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=settings_production

# Test Whisper installation
python -c "
import whisper
model = whisper.load_model('base')
print('✓ Whisper installed correctly')
"

# Test PyTorch
python -c "
import torch
print(f'✓ PyTorch version: {torch.__version__}')
if torch.cuda.is_available():
    print(f'✓ CUDA available: {torch.cuda.get_device_name(0)}')
else:
    print('⚠ CUDA not available (using CPU)')
"

# Test FFmpeg
ffmpeg -version

# Test Django with ML dependencies
python manage.py check
```

### 7. Resource Monitoring

Set up monitoring for AI/ML resource usage:

```bash
# Install monitoring tools
sudo apt install -y htop iotop nvidia-smi  # nvidia-smi only if GPU available

# Create resource monitoring script
cat > /home/cloudpanel/htdocs/yourdomain.com/backend/monitor_resources.sh << 'EOF'
#!/bin/bash
echo "=== System Resources ==="
echo "CPU Usage:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}'
echo ""
echo "Memory Usage:"
free -h
echo ""
echo "Disk Usage:"
df -h /home/cloudpanel/htdocs/yourdomain.com
echo ""
if command -v nvidia-smi &> /dev/null; then
    echo "GPU Usage:"
    nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv
fi
EOF

chmod +x /home/cloudpanel/htdocs/yourdomain.com/backend/monitor_resources.sh
```

### 8. Performance Optimization Tips

**For CPU-only servers:**
- Use `tiny` or `base` Whisper model
- Limit concurrent transcription jobs
- Consider using NCA Toolkit API for faster processing

**For GPU servers:**
- Use `medium` or `large` Whisper model
- Set `WHISPER_DEVICE=cuda` in `.env`
- Can handle more concurrent jobs

**Memory optimization:**
- Use model caching (already implemented)
- Clear cache periodically
- Monitor memory usage during peak times

---

## Deployment Steps

### Step 1: Prepare Code

1. **Build Frontend**:
```bash
cd frontend
npm install
npm run build
```

2. **Update Environment Variables**:
   - Copy `.env.production.example` to `.env`
   - Fill in all values
   - **IMPORTANT**: Generate a new SECRET_KEY:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 2: Upload to Server

1. **Via Git** (recommended):
```bash
# On server
cd /home/cloudpanel/htdocs/yourdomain.com
git clone your-repo-url .
```

2. **Via SFTP/SCP**:
```bash
# From local machine
scp -r backend frontend your-user@your-server:/home/cloudpanel/htdocs/yourdomain.com/
```

### Step 3: Setup Python Environment

```bash
cd /home/cloudpanel/htdocs/yourdomain.com/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Install PyTorch first (CPU or GPU version)
# For CPU-only:
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# OR for GPU (CUDA 11.8):
# pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
pip install -r requirements.txt

# Pre-download Whisper models (optional but recommended)
python -c "import whisper; print('Downloading Whisper models...'); whisper.load_model('base'); whisper.load_model('medium'); print('Models downloaded')"
```

### Step 4: Configure Environment

```bash
# Create .env file
nano .env
# Paste your environment variables
```

### Step 5: Run Migrations

```bash
cd backend
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=settings_production

# Load environment variables
set -a
source .env
set +a

python manage.py migrate
python manage.py collectstatic --noinput

# Verify AI/ML setup
python -c "
import whisper
import torch
print(f'✓ Whisper available')
print(f'✓ PyTorch {torch.__version__}')
print(f'✓ CUDA available: {torch.cuda.is_available()}')
"
```

### Step 6: Create Superuser

```bash
python manage.py createsuperuser
```

### Step 7: Setup Gunicorn Service

```bash
sudo nano /etc/systemd/system/rednote.service
# Paste the service file content
sudo systemctl daemon-reload
sudo systemctl enable rednote
sudo systemctl start rednote
```

### Step 8: Configure Nginx

CloudPanel will auto-generate Nginx config, but verify it matches the requirements above.

### Step 9: Restart Services

```bash
sudo systemctl restart rednote
sudo systemctl restart nginx
```

---

## Post-Deployment Verification

### 1. Test Authentication

```bash
# Test login
curl -X POST https://yourdomain.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"youruser","password":"yourpass"}'

# Should return access and refresh tokens
```

### 2. Test API with Token

```bash
# Use the access token from login
curl -X GET https://yourdomain.com/api/videos/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. Check Services

```bash
# Check Gunicorn
sudo systemctl status rednote

# Check Nginx
sudo systemctl status nginx

# Check logs
sudo journalctl -u rednote -f
tail -f /home/cloudpanel/htdocs/yourdomain.com/backend/logs/django.log
```

### 4. Test Frontend

- Visit `https://yourdomain.com`
- Should see login page
- Test login functionality
- Verify API calls work with authentication

---

## Frontend Authentication Integration

### 1. Create Auth Service

Create `frontend/src/services/auth.js`:

```javascript
import apiClient from '../api/client';
import { jwtDecode } from 'jwt-decode';

const TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user_data';

export const authService = {
  login: async (username, password) => {
    const response = await apiClient.post('/auth/login/', {
      username,
      password,
    });
    
    const { access, refresh, user } = response.data;
    
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    
    // Set default auth header
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${access}`;
    
    return { access, refresh, user };
  },

  logout: async () => {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    
    if (refreshToken) {
      try {
        await apiClient.post('/auth/logout/', { refresh: refreshToken });
      } catch (error) {
        console.error('Logout error:', error);
      }
    }
    
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    delete apiClient.defaults.headers.common['Authorization'];
  },

  getToken: () => localStorage.getItem(TOKEN_KEY),
  
  getRefreshToken: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  
  getUser: () => {
    const userStr = localStorage.getItem(USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
  },

  isAuthenticated: () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return false;
    
    try {
      const decoded = jwtDecode(token);
      const currentTime = Date.now() / 1000;
      return decoded.exp > currentTime;
    } catch {
      return false;
    }
  },

  refreshAccessToken: async () => {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!refreshToken) throw new Error('No refresh token');
    
    const response = await apiClient.post('/auth/refresh/', {
      refresh: refreshToken,
    });
    
    const { access } = response.data;
    localStorage.setItem(TOKEN_KEY, access);
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${access}`;
    
    return access;
  },
};
```

### 2. Update API Client

Update `frontend/src/api/client.js`:

```javascript
import axios from 'axios';
import { authService } from '../services/auth';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Add auth token to requests
apiClient.interceptors.request.use(
  (config) => {
    const token = authService.getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle token refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        await authService.refreshAccessToken();
        originalRequest.headers.Authorization = `Bearer ${authService.getToken()}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        authService.logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
```

### 3. Create Protected Route Component

Create `frontend/src/components/ProtectedRoute.jsx`:

```javascript
import { Navigate } from 'react-router-dom';
import { authService } from '../services/auth';

export default function ProtectedRoute({ children }) {
  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
}
```

### 4. Create Login Page

Create `frontend/src/pages/Login.jsx`:

```javascript
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/auth';
import toast from 'react-hot-toast';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await authService.login(username, password);
      toast.success('Login successful!');
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8">
        <h2 className="text-2xl font-bold mb-6 text-center">Login</h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 border rounded-md"
              required
            />
          </div>
          <div className="mb-6">
            <label className="block text-sm font-medium mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border rounded-md"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
      </div>
    </div>
  );
}
```

### 5. Update App Router

Update `frontend/src/App.jsx`:

```javascript
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
// ... other imports

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              {/* Your existing routes */}
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
```

---

## Troubleshooting

### Common Issues

1. **502 Bad Gateway**
   - Check Gunicorn is running: `sudo systemctl status rednote`
   - Check logs: `sudo journalctl -u rednote -n 50`
   - Verify port in Gunicorn config matches Nginx proxy

2. **Static files not loading**
   - Run `python manage.py collectstatic`
   - Check Nginx static file location
   - Verify file permissions

3. **Database connection errors**
   - Verify PostgreSQL is running
   - Check database credentials in `.env`
   - Test connection: `psql -U rednote_user -d rednote_db`

4. **Authentication not working**
   - Check JWT tokens in browser DevTools
   - Verify API client includes Authorization header
   - Check backend logs for authentication errors

5. **WebSocket not connecting**
   - Verify Redis is running
   - Check Channels routing
   - Verify Nginx WebSocket proxy configuration

6. **Whisper/ML Model Errors**
   - **Out of Memory**: Reduce `WHISPER_MODEL_SIZE` to `tiny` or `base`
   - **Model download fails**: Check internet connection, models download on first use
   - **CUDA errors**: Verify GPU drivers and CUDA installation
   - **Slow transcription**: Consider using GPU or NCA Toolkit API
   - Check model cache: `ls -lh ~/.cache/whisper/`

7. **PyTorch Installation Issues**
   - **CPU version**: Use `--index-url https://download.pytorch.org/whl/cpu`
   - **GPU version**: Match CUDA version with installed CUDA toolkit
   - **Import errors**: Reinstall PyTorch: `pip uninstall torch torchaudio && pip install torch torchaudio`

8. **FFmpeg Errors**
   - Verify installation: `ffmpeg -version`
   - Install if missing: `sudo apt install ffmpeg`
   - Check codec support: `ffmpeg -codecs`

9. **AI API Key Errors**
   - Verify API keys in `.env` file
   - Check API keys in Django admin (AI Provider Settings)
   - Test API keys manually:
     ```bash
     # Test OpenAI
     curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
     
     # Test Gemini
     curl "https://generativelanguage.googleapis.com/v1/models?key=$GOOGLE_API_KEY"
     ```

10. **High Memory Usage**
    - Monitor with: `htop` or `free -h`
    - Reduce Whisper model size
    - Limit concurrent transcription jobs
    - Clear Whisper cache: `rm -rf ~/.cache/whisper/*.pt`
    - Restart Gunicorn workers if memory leaks occur

---

## Security Checklist

- [ ] DEBUG = False in production
- [ ] Strong SECRET_KEY set
- [ ] ALLOWED_HOSTS configured
- [ ] SSL/HTTPS enabled
- [ ] Database credentials secured
- [ ] Static files permissions set correctly
- [ ] Firewall configured (only 80, 443, 22 open)
- [ ] Regular backups configured
- [ ] Log monitoring set up
- [ ] Rate limiting configured (optional)
- [ ] CORS properly configured
- [ ] Security headers enabled
- [ ] AI API keys secured in `.env` (never commit to git)
- [ ] Whisper model cache permissions set correctly
- [ ] Media files access restricted (authentication required)

---

## Next Steps

1. Set up automated backups
2. Configure monitoring (e.g., Sentry for error tracking)
3. Set up CI/CD pipeline
4. Configure rate limiting
5. Set up log aggregation
6. Regular security updates
7. **AI/ML Optimization**:
   - Monitor transcription performance
   - Adjust Whisper model size based on server resources
   - Consider GPU upgrade if processing is slow
   - Set up model cache cleanup cron job
   - Monitor API usage and costs
8. **Performance Tuning**:
   - Optimize Gunicorn worker count for your CPU
   - Configure Redis for better WebSocket performance
   - Set up CDN for static/media files (optional)
   - Implement job queue (Celery) for long-running AI tasks (optional)

---

**Note**: This is a comprehensive plan. You may need to adjust based on your specific CloudPanel version and server configuration.

---

## AI/ML Quick Reference

### Model Selection Guide

| Model | RAM Usage | Speed (CPU) | Speed (GPU) | Accuracy | Use Case |
|-------|-----------|-------------|-------------|----------|----------|
| `tiny` | ~1GB | Fastest | Very Fast | Basic | Quick testing, low-resource servers |
| `base` | ~1GB | Fast | Very Fast | Good | Balanced performance (recommended for CPU) |
| `small` | ~2GB | Medium | Very Fast | Better | Better accuracy, moderate resources |
| `medium` | ~5GB | Slow | Fast | High | **Recommended for production** |
| `large` | ~10GB | Very Slow | Medium | Best | Maximum accuracy, requires 16GB+ RAM |

### Environment Variables Quick Reference

```bash
# Required for AI Processing
OPENAI_API_KEY=sk-...          # OpenAI API key
ANTHROPIC_API_KEY=sk-ant-...   # Anthropic API key  
GOOGLE_API_KEY=...              # Google Gemini API key

# Whisper Configuration
WHISPER_MODEL_SIZE=medium       # tiny|base|small|medium|large
WHISPER_DEVICE=cpu              # cpu|cuda (use cuda if GPU available)

# Optional: NCA Toolkit API (for faster transcription)
NCA_API_ENABLED=false           # true|false
NCA_API_URL=http://localhost:8080
NCA_API_KEY=your-key
```

### Performance Benchmarks

**Transcription Speed (1-minute video):**
- CPU + tiny: ~10 seconds
- CPU + base: ~20 seconds
- CPU + medium: ~60 seconds
- GPU + medium: ~5-10 seconds
- GPU + large: ~15-20 seconds

**Memory Usage:**
- Base model: ~1GB RAM
- Medium model: ~5GB RAM
- Large model: ~10GB RAM
- Plus video processing: +2-4GB RAM

### Common Commands

```bash
# Check GPU availability
nvidia-smi

# Test Whisper installation
python -c "import whisper; model = whisper.load_model('base'); print('OK')"

# Check PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Clear Whisper cache
rm -rf ~/.cache/whisper/*.pt

# Monitor resources
htop
nvidia-smi -l 1  # GPU monitoring (if available)
```

### Troubleshooting Quick Fixes

| Issue | Solution |
|-------|----------|
| Out of memory | Reduce `WHISPER_MODEL_SIZE` to `tiny` or `base` |
| Slow transcription | Use GPU (`WHISPER_DEVICE=cuda`) or NCA API |
| Model download fails | Check internet, manually download models |
| CUDA errors | Verify GPU drivers: `nvidia-smi` |
| API key errors | Check `.env` file and Django admin settings |

