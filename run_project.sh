#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo "Stopping servers..."
    kill $DJANGO_PID 2>/dev/null
    kill $REACT_PID 2>/dev/null
    echo "Stopping NCA Toolkit..."
    docker stop nca-toolkit 2>/dev/null
    exit
}

# Trap SIGINT (Ctrl+C)
trap cleanup SIGINT

echo "Starting RedNote Project..."

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH."
    echo "NCA Toolkit requires Docker to run."
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH."
    exit 1
fi

# Check for Node.js and npm
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo "Error: Node.js and npm are not installed or not in PATH."
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
cd legacy/root_debris

# Check for Python 3.10 (recommended) or 3.11, 3.9 (required for TTS per guide)
PYTHON_CMD=""
if command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
    echo "Using Python 3.10 (recommended for TTS)"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    echo "Using Python 3.11"
elif command -v python3.9 &> /dev/null; then
    PYTHON_CMD="python3.9"
    echo "Using Python 3.9"
else
    # Try to find Python 3.9 from Xcode (macOS)
    if [ -f "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3" ]; then
        PYTHON_CMD="/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3"
        echo "Using Python 3.9 from Xcode"
    else
        echo "Error: Python 3.9, 3.10, or 3.11 is required for TTS."
        echo "Please install Python 3.10: brew install python@3.10"
        exit 1
    fi
fi

# Verify Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo "Python version: $PYTHON_VERSION"

# Check if Python version is compatible (3.9-3.11, NOT 3.12+)
if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 9 ] && [ "$PYTHON_MINOR" -le 11 ]; then
    echo "✓ Python version is compatible with TTS"
else
    echo "Warning: Python 3.9-3.11 recommended for TTS. Current: $PYTHON_VERSION"
    echo "TTS features may not work properly."
fi

# Recreate venv if it exists with wrong Python version
if [ -d "venv" ] && [ -f "venv/pyvenv.cfg" ]; then
    VENV_PYTHON=$(grep "version" venv/pyvenv.cfg | awk '{print $3}' || echo "")
    if [ ! -z "$VENV_PYTHON" ]; then
        VENV_MAJOR=$(echo $VENV_PYTHON | cut -d. -f1)
        VENV_MINOR=$(echo $VENV_PYTHON | cut -d. -f2)
        
        # Recreate if using Python 3.12+ or if major/minor version differs significantly
        if [ "$VENV_MAJOR" -eq 3 ] && ([ "$VENV_MINOR" -ge 12 ] || [ "$VENV_MINOR" -lt 9 ]); then
            echo "Recreating virtual environment with Python $PYTHON_VERSION (current venv uses Python $VENV_PYTHON)..."
            rm -rf venv
        fi
    fi
fi

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment with $PYTHON_CMD ($PYTHON_VERSION)..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment."
        exit 1
    fi
fi

source venv/bin/activate
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

echo "Installing Python dependencies (this may take a few minutes)..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python dependencies."
    echo "You may need to install system dependencies:"
    echo "  macOS: brew install ffmpeg portaudio"
    exit 1
fi
echo "✓ Python dependencies installed successfully."
cd ../..

# Install npm dependencies
echo "Installing npm dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing npm packages (this may take a few minutes)..."
    npm install
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install npm dependencies."
        exit 1
    fi
else
    echo "npm dependencies already installed, skipping..."
fi
cd ..
echo "npm dependencies installed."

# Start NCA Toolkit (Docker)
echo "Starting NCA Toolkit (Transcription Service)..."
# Remove any existing container with same name to avoid conflict
docker rm -f nca-toolkit &> /dev/null
# Run container
docker run --rm -d -p 8080:8080 --name nca-toolkit -e API_KEY=test_api_key stephengpope/no-code-architects-toolkit
if [ $? -ne 0 ]; then
    echo "Error: Failed to start NCA Toolkit container."
    echo "Please ensure Docker is running and you have permissions."
    exit 1
fi
echo "NCA Toolkit started on port 8080."

# Wait a moment for NCA Toolkit to be ready
sleep 2

# Check if ports are available
DJANGO_PORT=8000
REACT_PORT=5173

if lsof -ti:$DJANGO_PORT &> /dev/null; then
    echo "Warning: Port $DJANGO_PORT is already in use."
    echo "Django will try to start, but may fail. Please free the port or stop the conflicting service."
fi

if lsof -ti:$REACT_PORT &> /dev/null; then
    echo "Warning: Port $REACT_PORT is already in use."
    echo "React will try to start, but may fail. Please free the port or stop the conflicting service."
fi

# Start Django Backend
echo "Starting Django Backend..."
cd legacy/root_debris
source venv/bin/activate

# Run migrations if needed
echo "Running Django migrations..."
python3 manage.py migrate --noinput > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Warning: Migrations may have failed, but continuing..."
fi

# Start Django server
python3 manage.py runserver 0.0.0.0:$DJANGO_PORT > /tmp/django.log 2>&1 &
DJANGO_PID=$!

# Wait for Django to be ready (check if port is listening)
echo "Waiting for Django to start..."
MAX_WAIT=30
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if lsof -ti:$DJANGO_PORT &> /dev/null; then
        # Port is listening, check if it's responding
        if curl -s http://localhost:$DJANGO_PORT/admin/ > /dev/null 2>&1; then
            echo "Django is ready on port $DJANGO_PORT"
            break
        fi
    fi
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

# Check if Django started successfully
if ! lsof -ti:$DJANGO_PORT &> /dev/null; then
    echo "Error: Django failed to start on port $DJANGO_PORT after $MAX_WAIT seconds."
    echo "Check /tmp/django.log for errors:"
    tail -20 /tmp/django.log
    cleanup
    exit 1
fi

cd ../..

# Start React Frontend
echo "Starting React Frontend..."
cd frontend
npm run dev -- --host &
REACT_PID=$!
sleep 2
# Check if React started successfully
if ! kill -0 $REACT_PID 2>/dev/null; then
    echo "Error: React failed to start. Port $REACT_PORT may be in use."
    echo "Please stop the service using port $REACT_PORT and try again."
    cleanup
    exit 1
fi
cd ..

echo ""
echo "=========================================="
echo "All services are running!"
echo "=========================================="
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "NCA Toolkit: http://localhost:8080"
echo "=========================================="
echo "Press Ctrl+C to stop all services."
echo ""

# Wait for processes
wait $DJANGO_PID $REACT_PID
