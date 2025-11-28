#!/bin/bash

# Set up logging directory
LOG_DIR="$HOME/.rednote_logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
MAIN_LOG="$LOG_DIR/run_project_${TIMESTAMP}.log"
ERROR_LOG="$LOG_DIR/errors_${TIMESTAMP}.log"
DJANGO_LOG="$LOG_DIR/django_${TIMESTAMP}.log"
REACT_LOG="$LOG_DIR/react_${TIMESTAMP}.log"
DOCKER_LOG="$LOG_DIR/docker_${TIMESTAMP}.log"
PIP_LOG="$LOG_DIR/pip_${TIMESTAMP}.log"
NPM_LOG="$LOG_DIR/npm_${TIMESTAMP}.log"

# Logging functions
log_info() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1" | tee -a "$MAIN_LOG"
}

log_error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$MAIN_LOG" | tee -a "$ERROR_LOG"
}

log_warning() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1" | tee -a "$MAIN_LOG"
}

log_debug() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] DEBUG: $1" | tee -a "$MAIN_LOG"
}

# Function to log system information
log_system_info() {
    log_info "=== System Information ==="
    log_info "OS: $(uname -a)"
    log_info "Shell: $SHELL"
    log_info "User: $(whoami)"
    log_info "Working Directory: $(pwd)"
    log_info "Python: $(python3 --version 2>&1 || echo 'Not found')"
    log_info "Node: $(node --version 2>&1 || echo 'Not found')"
    log_info "npm: $(npm --version 2>&1 || echo 'Not found')"
    log_info "Docker: $(docker --version 2>&1 || echo 'Not found')"
    log_info "Log Directory: $LOG_DIR"
    log_info "========================="
}

# Function to check command availability with detailed error
check_command() {
    local cmd=$1
    local name=$2
    if ! command -v "$cmd" &> /dev/null; then
        log_error "$name is not installed or not in PATH."
        log_error "Please install $name and ensure it's in your PATH."
        log_error "Command checked: $cmd"
        return 1
    fi
    local version=$($cmd --version 2>&1 || echo "version unknown")
    log_debug "$name found: $version"
    return 0
}

# Function to kill background processes on exit
cleanup() {
    log_info "Stopping servers..."
    if [ ! -z "$DJANGO_PID" ]; then
        log_debug "Killing Django (PID: $DJANGO_PID)"
        kill $DJANGO_PID 2>/dev/null
    fi
    if [ ! -z "$REACT_PID" ]; then
        log_debug "Killing React (PID: $REACT_PID)"
        kill $REACT_PID 2>/dev/null
    fi
    log_info "Stopping NCA Toolkit..."
    docker stop nca-toolkit 2>/dev/null || true
    log_info "Cleanup complete. Logs saved to: $LOG_DIR"
    exit
}

# Trap SIGINT (Ctrl+C) and errors
trap cleanup SIGINT
trap 'log_error "Script failed at line $LINENO. Check logs in $LOG_DIR"' ERR

log_info "Starting RedNote Project..."
log_system_info

# Check for Docker (optional - only needed for NCA Toolkit)
log_info "Checking for Docker (optional for NCA Toolkit)..."
if ! check_command docker "Docker"; then
    log_warning "Docker is not installed. NCA Toolkit will not be available."
    log_warning "Installation: https://docs.docker.com/get-docker/"
    NCA_AVAILABLE=false
else
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_warning "Docker daemon is not running. NCA Toolkit will not be available."
        log_warning "Please start Docker Desktop or the Docker service to use NCA Toolkit."
        NCA_AVAILABLE=false
    else
        log_info "✓ Docker is running (NCA Toolkit available)"
        NCA_AVAILABLE=true
    fi
fi

# Check for Python
log_info "Checking for Python..."
if ! check_command python3 "Python 3"; then
    log_error "Python 3 is required for the backend."
    exit 1
fi

# Check for Node.js and npm
log_info "Checking for Node.js and npm..."
if ! check_command node "Node.js"; then
    log_error "Node.js is required for the frontend."
    exit 1
fi
if ! check_command npm "npm"; then
    log_error "npm is required for the frontend."
    exit 1
fi

# Install Python dependencies
log_info "Setting up Python environment..."
cd legacy/root_debris || {
    log_error "Failed to change directory to legacy/root_debris"
    log_error "Current directory: $(pwd)"
    exit 1
}

# Check for Python 3.10 (recommended) or 3.11, 3.9 (required for TTS per guide)
PYTHON_CMD=""
if command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
    log_info "Using Python 3.10 (recommended for TTS)"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    log_info "Using Python 3.11"
elif command -v python3.9 &> /dev/null; then
    PYTHON_CMD="python3.9"
    log_info "Using Python 3.9"
else
    # Try to find Python 3.9 from Xcode (macOS)
    if [ -f "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3" ]; then
        PYTHON_CMD="/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3"
        log_info "Using Python 3.9 from Xcode"
    else
        log_error "Python 3.9, 3.10, or 3.11 is required for TTS."
        log_error "Please install Python 3.10: brew install python@3.10"
        log_error "Or download from: https://www.python.org/downloads/"
        exit 1
    fi
fi

# Verify Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

log_info "Python version: $PYTHON_VERSION (from: $PYTHON_CMD)"

# Check if Python version is compatible (3.9-3.11, NOT 3.12+)
if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 9 ] && [ "$PYTHON_MINOR" -le 11 ]; then
    log_info "✓ Python version is compatible with TTS"
else
    log_warning "Python 3.9-3.11 recommended for TTS. Current: $PYTHON_VERSION"
    log_warning "TTS features may not work properly."
fi

# Recreate venv if it exists with wrong Python version
if [ -d "venv" ] && [ -f "venv/pyvenv.cfg" ]; then
    VENV_PYTHON=$(grep "version" venv/pyvenv.cfg | awk '{print $3}' || echo "")
    if [ ! -z "$VENV_PYTHON" ]; then
        VENV_MAJOR=$(echo $VENV_PYTHON | cut -d. -f1)
        VENV_MINOR=$(echo $VENV_PYTHON | cut -d. -f2)
        
        # Recreate if using Python 3.12+ or if major/minor version differs significantly
        if [ "$VENV_MAJOR" -eq 3 ] && ([ "$VENV_MINOR" -ge 12 ] || [ "$VENV_MINOR" -lt 9 ]); then
            log_info "Recreating virtual environment with Python $PYTHON_VERSION (current venv uses Python $VENV_PYTHON)..."
            rm -rf venv
        fi
    fi
fi

if [ ! -d "venv" ]; then
    log_info "Creating Python virtual environment with $PYTHON_CMD ($PYTHON_VERSION)..."
    if ! $PYTHON_CMD -m venv venv 2>&1 | tee -a "$PIP_LOG"; then
        log_error "Failed to create virtual environment."
        log_error "Python command: $PYTHON_CMD"
        log_error "Python version: $PYTHON_VERSION"
        log_error "Check $PIP_LOG for details"
        exit 1
    fi
    log_info "✓ Virtual environment created"
else
    log_info "✓ Virtual environment already exists"
fi

log_info "Activating virtual environment..."
source venv/bin/activate || {
    log_error "Failed to activate virtual environment"
    exit 1
}
log_debug "Virtual environment activated: $(which python)"

# Check if dependencies need to be installed
log_info "Checking Python dependencies..."
NEEDS_INSTALL=false
if [ ! -f "requirements.txt" ]; then
    log_error "requirements.txt not found in $(pwd)"
    exit 1
fi

if [ ! -f "venv/.deps_installed" ]; then
    NEEDS_INSTALL=true
    log_debug "No .deps_installed marker found"
else
    # Check if requirements.txt has changed
    if [ "requirements.txt" -nt "venv/.deps_installed" ]; then
        NEEDS_INSTALL=true
        log_debug "requirements.txt has been modified"
    fi
fi

# Quick check if Django is installed (as a proxy for all dependencies)
if pip show django > /dev/null 2>&1; then
    if [ "$NEEDS_INSTALL" = false ]; then
        log_info "✓ Python dependencies already installed"
    else
        # requirements.txt changed, need to update
        log_info "Updating Python dependencies..."
        log_debug "Upgrading pip..."
        if ! pip install --upgrade pip >> "$PIP_LOG" 2>&1; then
            log_warning "pip upgrade had issues, but continuing..."
        fi
        # Run pip install and capture output
        log_info "Installing/updating packages from requirements.txt..."
        PIP_OUTPUT=$(pip install -r requirements.txt 2>&1)
        PIP_EXIT=$?
        echo "$PIP_OUTPUT" >> "$PIP_LOG"
        # Only show output if there are actual changes (not just "already satisfied")
        echo "$PIP_OUTPUT" | grep -v "Requirement already satisfied" | grep -v "^$" || true
        if [ $PIP_EXIT -ne 0 ]; then
            log_error "Failed to update Python dependencies."
            log_error "Exit code: $PIP_EXIT"
            log_error "Full pip output saved to: $PIP_LOG"
            log_error "Common issues:"
            log_error "  - Missing system dependencies (macOS: brew install ffmpeg portaudio)"
            log_error "  - Network issues or package repository problems"
            log_error "  - Incompatible package versions"
            echo "$PIP_OUTPUT" | tail -30
            exit 1
        fi
        touch venv/.deps_installed
        log_info "✓ Python dependencies updated."
    fi
else
    # Dependencies not installed
    log_info "Installing Python dependencies (this may take a few minutes)..."
    log_debug "Upgrading pip..."
    if ! pip install --upgrade pip >> "$PIP_LOG" 2>&1; then
        log_warning "pip upgrade had issues, but continuing..."
    fi
    # Show progress for initial installation, filter out "already satisfied"
    log_info "Installing packages from requirements.txt..."
    PIP_OUTPUT=$(pip install -r requirements.txt 2>&1)
    PIP_EXIT=$?
    echo "$PIP_OUTPUT" >> "$PIP_LOG"
    echo "$PIP_OUTPUT" | grep -v "Requirement already satisfied" | grep -v "^$" || true
    if [ $PIP_EXIT -ne 0 ]; then
        log_error "Failed to install Python dependencies."
        log_error "Exit code: $PIP_EXIT"
        log_error "Full pip output saved to: $PIP_LOG"
        log_error "You may need to install system dependencies:"
        log_error "  macOS: brew install ffmpeg portaudio"
        log_error "  Linux: sudo apt-get install ffmpeg portaudio19-dev python3-dev"
        log_error "Last 30 lines of pip output:"
        echo "$PIP_OUTPUT" | tail -30
        exit 1
    fi
    touch venv/.deps_installed
    log_info "✓ Python dependencies installed successfully."
fi

# Ensure PyTorch is installed with GPU support (MPS for Mac, CUDA for NVIDIA)
log_info "Installing/updating PyTorch with GPU support..."
if pip install torch torchvision torchaudio >> "$PIP_LOG" 2>&1; then
    log_info "✓ PyTorch installed/updated successfully"
    log_debug "PyTorch version: $(pip show torch | grep Version | awk '{print $2}' 2>/dev/null || echo 'unknown')"
else
    log_warning "PyTorch installation had issues, but continuing..."
    log_warning "Check $PIP_LOG for details"
fi

# Install AI Provider SDKs (for metadata generation and AI features)
log_info "Installing AI Provider SDKs..."
if pip install google-generativeai openai anthropic >> "$PIP_LOG" 2>&1; then
    log_info "✓ AI Provider SDKs installed/updated successfully"
else
    log_warning "AI Provider SDKs installation had issues, but continuing..."
    log_warning "Note: REST API fallback will be used if SDKs are not available"
    log_warning "Check $PIP_LOG for details"
fi

cd ../.. || {
    log_error "Failed to return to project root"
    exit 1
}

# Install npm dependencies
log_info "Setting up frontend dependencies..."
cd frontend || {
    log_error "Failed to change directory to frontend"
    log_error "Current directory: $(pwd)"
    exit 1
}

if [ ! -f "package.json" ]; then
    log_error "package.json not found in $(pwd)"
    exit 1
fi

if [ ! -d "node_modules" ]; then
    log_info "Installing npm dependencies (this may take a few minutes)..."
    log_debug "Node version: $(node --version)"
    log_debug "npm version: $(npm --version)"
    if npm install >> "$NPM_LOG" 2>&1; then
        log_info "✓ npm dependencies installed successfully."
    else
        log_error "Failed to install npm dependencies."
        log_error "Full npm output saved to: $NPM_LOG"
        log_error "Common issues:"
        log_error "  - Network connectivity problems"
        log_error "  - Corrupted node_modules or package-lock.json"
        log_error "  - Insufficient disk space"
        log_error "  - Permission issues"
        log_error "Last 30 lines of npm output:"
        tail -30 "$NPM_LOG"
        exit 1
    fi
else
    # Check if package.json has changed
    if [ "package.json" -nt "node_modules/.package-lock.json" ] 2>/dev/null || [ ! -f "node_modules/.package-lock.json" ]; then
        log_info "Updating npm dependencies..."
        if npm install >> "$NPM_LOG" 2>&1; then
            touch node_modules/.package-lock.json
            log_info "✓ npm dependencies updated."
        else
            log_warning "npm update had issues, but continuing..."
            log_warning "Check $NPM_LOG for details"
        fi
    else
        log_info "✓ npm dependencies already installed"
    fi
fi
cd .. || {
    log_error "Failed to return to project root"
    exit 1
}

# Start NCA Toolkit (Docker) - Optional
if [ "$NCA_AVAILABLE" = true ]; then
    log_info "Starting NCA Toolkit (optional)..."
    # Remove any existing container with same name to avoid conflict
    log_debug "Removing any existing nca-toolkit container..."
    docker rm -f nca-toolkit >> "$DOCKER_LOG" 2>&1 || true

    # Check if image exists
    if ! docker images | grep -q "stephengpope/no-code-architects-toolkit"; then
        log_info "Pulling NCA Toolkit image (this may take a few minutes)..."
        if ! docker pull stephengpope/no-code-architects-toolkit >> "$DOCKER_LOG" 2>&1; then
            log_warning "Failed to pull NCA Toolkit image. NCA Toolkit will not be available."
            log_warning "Check $DOCKER_LOG for details"
            log_warning "Continuing without NCA Toolkit..."
            NCA_AVAILABLE=false
        fi
    fi

    if [ "$NCA_AVAILABLE" = true ]; then
        # Run container
        log_info "Starting NCA Toolkit container..."
        # Check if port 8080 is available before starting
        if lsof -ti:8080 &> /dev/null; then
            PORT_PID=$(lsof -ti:8080 | head -1)
            # Check if it's already our container
            if ! docker ps --format '{{.Names}}' | grep -q "^nca-toolkit$"; then
                log_warning "Port 8080 is in use (PID: $PORT_PID). Attempting to start container anyway..."
                log_warning "If container fails, NCA Toolkit will not be available"
            fi
        fi

        DOCKER_OUTPUT=$(docker run --rm -d -p 8080:8080 --name nca-toolkit -e API_KEY=test_api_key stephengpope/no-code-architects-toolkit 2>&1)
        DOCKER_EXIT=$?
        echo "$DOCKER_OUTPUT" >> "$DOCKER_LOG"

        if [ $DOCKER_EXIT -ne 0 ]; then
            # Check if error is about port already in use
            if echo "$DOCKER_OUTPUT" | grep -qiE "(port.*already|address.*already|bind.*already)"; then
                log_warning "Port 8080 is already in use. NCA Toolkit will not be available."
                log_warning "To find what's using port 8080: lsof -i :8080"
            else
                log_warning "Failed to start NCA Toolkit container."
                log_warning "Docker output: $DOCKER_OUTPUT"
                log_warning "Check $DOCKER_LOG for details"
            fi
            log_info "Continuing without NCA Toolkit - other services will run normally"
            NCA_AVAILABLE=false
        else
            # Wait a moment for NCA Toolkit to be ready
            log_debug "Waiting for NCA Toolkit to initialize..."
            sleep 2

            # Verify container is running
            sleep 2  # Give container a moment to start
            if docker ps --format '{{.Names}}' | grep -q "^nca-toolkit$"; then
                log_info "✓ NCA Toolkit container is running"
                # Verify it's actually listening on the port
                if lsof -ti:$NCA_PORT &> /dev/null; then
                    log_debug "✓ NCA Toolkit is listening on port $NCA_PORT"
                else
                    log_warning "NCA Toolkit container is running but port $NCA_PORT may not be accessible"
                fi
            else
                log_warning "NCA Toolkit container started but is not running"
                log_warning "Container logs:"
                docker logs nca-toolkit 2>&1 | tail -20 | tee -a "$DOCKER_LOG" || true
                log_info "Continuing without NCA Toolkit - other services will run normally"
                NCA_AVAILABLE=false
            fi
        fi
    fi
else
    log_info "Skipping NCA Toolkit (Docker not available or not running)"
fi

# Check if ports are available
DJANGO_PORT=8000
REACT_PORT=5173
NCA_PORT=8080

log_info "Checking port availability..."
log_debug "Django port: $DJANGO_PORT, React port: $REACT_PORT, NCA port: $NCA_PORT"

if lsof -ti:$DJANGO_PORT &> /dev/null; then
    PORT_PID=$(lsof -ti:$DJANGO_PORT | head -1)
    PORT_PROCESS=$(ps -p $PORT_PID -o comm= 2>/dev/null || echo "unknown")
    PORT_CMD=$(ps -p $PORT_PID -o args= 2>/dev/null | head -c 100 || echo "unknown")
    
    # Check if it's a previous Django instance
    if echo "$PORT_CMD" | grep -qE "(manage.py|runserver|django)" 2>/dev/null; then
        log_warning "Port $DJANGO_PORT is already in use by a previous Django instance (PID: $PORT_PID)"
        log_info "Killing previous instance..."
        kill $PORT_PID 2>/dev/null
        sleep 1
        # Verify it's killed
        if lsof -ti:$DJANGO_PORT &> /dev/null; then
            log_error "Failed to kill process. Please manually kill it: kill $PORT_PID"
        else
            log_info "✓ Previous instance killed"
        fi
    else
        log_warning "Port $DJANGO_PORT is already in use by: $PORT_PROCESS (PID: $PORT_PID)"
        log_warning "Command: $PORT_CMD"
        log_warning "Django will try to start, but may fail. To free the port, run: kill $PORT_PID"
    fi
fi

if lsof -ti:$REACT_PORT &> /dev/null; then
    PORT_PID=$(lsof -ti:$REACT_PORT | head -1)
    PORT_PROCESS=$(ps -p $PORT_PID -o comm= 2>/dev/null || echo "unknown")
    PORT_CMD=$(ps -p $PORT_PID -o args= 2>/dev/null | head -c 100 || echo "unknown")
    
    # Check if it's a previous React/Vite instance
    if echo "$PORT_CMD" | grep -qE "(vite|node.*dev|react)" 2>/dev/null; then
        log_warning "Port $REACT_PORT is already in use by a previous React/Vite instance (PID: $PORT_PID)"
        log_info "Killing previous instance..."
        kill $PORT_PID 2>/dev/null
        sleep 1
        # Verify it's killed
        if lsof -ti:$REACT_PORT &> /dev/null; then
            log_error "Failed to kill process. Please manually kill it: kill $PORT_PID"
        else
            log_info "✓ Previous instance killed"
        fi
    else
        log_warning "Port $REACT_PORT is already in use by: $PORT_PROCESS (PID: $PORT_PID)"
        log_warning "Command: $PORT_CMD"
        log_warning "React will try to start, but may fail. To free the port, run: kill $PORT_PID"
    fi
fi

if lsof -ti:$NCA_PORT &> /dev/null; then
    PORT_PID=$(lsof -ti:$NCA_PORT | head -1)
    PORT_PROCESS=$(ps -p $PORT_PID -o comm= 2>/dev/null || echo "unknown")
    
    # Check if it's the NCA Toolkit container
    if [ "$NCA_AVAILABLE" = true ] && docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^nca-toolkit$"; then
        log_info "Port $NCA_PORT is in use by existing NCA Toolkit container (this is expected)"
    else
        log_debug "Port $NCA_PORT is in use by: $PORT_PROCESS (PID: $PORT_PID)"
        log_debug "This is fine - NCA Toolkit is optional"
    fi
fi

# Start Django Backend
log_info "Starting Django Backend..."
cd legacy/root_debris || {
    log_error "Failed to change directory to legacy/root_debris"
    exit 1
}
source venv/bin/activate || {
    log_error "Failed to activate virtual environment"
    exit 1
}

# Check if manage.py exists
if [ ! -f "manage.py" ]; then
    log_error "manage.py not found in $(pwd)"
    exit 1
fi

# Run migrations
log_info "Running database migrations..."
MIGRATION_OUTPUT=$(python3 manage.py migrate --noinput 2>&1)
MIGRATION_EXIT=$?
echo "$MIGRATION_OUTPUT" | tee -a "$DJANGO_LOG"
if [ $MIGRATION_EXIT -ne 0 ]; then
    log_error "Database migrations failed."
    log_error "Exit code: $MIGRATION_EXIT"
    log_error "Migration output saved to: $DJANGO_LOG"
    log_error "Common issues:"
    log_error "  - Database connection problems"
    log_error "  - Missing database file or permissions"
    log_error "  - Migration conflicts"
    exit 1
fi
log_info "✓ Migrations completed"

# Start Django server
log_info "Starting Django server on port $DJANGO_PORT..."
log_debug "Django log file: $DJANGO_LOG"
python3 manage.py runserver 0.0.0.0:$DJANGO_PORT >> "$DJANGO_LOG" 2>&1 &
DJANGO_PID=$!
log_debug "Django PID: $DJANGO_PID"

# Wait for Django to be ready (check if port is listening)
MAX_WAIT=30
WAIT_COUNT=0
log_info "Waiting for Django to start (max ${MAX_WAIT}s)..."
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if lsof -ti:$DJANGO_PORT &> /dev/null; then
        # Port is listening, check if it's responding
        if curl -s http://localhost:$DJANGO_PORT/admin/ > /dev/null 2>&1; then
            log_info "✓ Django is responding"
            break
        fi
    fi
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    if [ $((WAIT_COUNT % 5)) -eq 0 ]; then
        log_debug "Still waiting... ($WAIT_COUNT/$MAX_WAIT seconds)"
    fi
done

# Check if Django started successfully
if ! lsof -ti:$DJANGO_PORT &> /dev/null; then
    log_error "Django failed to start on port $DJANGO_PORT after $MAX_WAIT seconds."
    log_error "Django log file: $DJANGO_LOG"
    log_error "Last 50 lines of Django log:"
    tail -50 "$DJANGO_LOG" | tee -a "$ERROR_LOG"
    log_error "Process status:"
    if kill -0 $DJANGO_PID 2>/dev/null; then
        log_error "Django process (PID: $DJANGO_PID) is still running but not listening on port"
    else
        log_error "Django process (PID: $DJANGO_PID) has exited"
    fi
    log_error "Common issues:"
    log_error "  - Port already in use"
    log_error "  - Database connection errors"
    log_error "  - Missing environment variables"
    log_error "  - Import errors or missing dependencies"
    cleanup
    exit 1
fi

log_info "✓ Django is running on port $DJANGO_PORT"

cd ../.. || {
    log_error "Failed to return to project root"
    exit 1
}

# Start React Frontend
log_info "Starting React Frontend..."
cd frontend || {
    log_error "Failed to change directory to frontend"
    exit 1
}

log_info "Starting Vite dev server on port $REACT_PORT..."
log_debug "React log file: $REACT_LOG"
npm run dev -- --host >> "$REACT_LOG" 2>&1 &
REACT_PID=$!
log_debug "React PID: $REACT_PID"

# Wait a bit for React to start
sleep 3

# Check if React started successfully
if ! kill -0 $REACT_PID 2>/dev/null; then
    log_error "React failed to start. Process exited immediately."
    log_error "React log file: $REACT_LOG"
    log_error "Last 50 lines of React log:"
    tail -50 "$REACT_LOG" | tee -a "$ERROR_LOG"
    log_error "Common issues:"
    log_error "  - Port $REACT_PORT may be in use"
    log_error "  - Missing dependencies (run: npm install)"
    log_error "  - Configuration errors in vite.config.js"
    log_error "  - Syntax errors in source code"
    cleanup
    exit 1
fi

# Check if port is listening
MAX_WAIT=15
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if lsof -ti:$REACT_PORT &> /dev/null; then
        log_info "✓ React is running on port $REACT_PORT"
        break
    fi
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if ! lsof -ti:$REACT_PORT &> /dev/null; then
    log_warning "React process is running but port $REACT_PORT is not listening yet"
    log_warning "This may be normal if Vite is still starting up"
    log_warning "Check $REACT_LOG for details"
fi

cd .. || {
    log_error "Failed to return to project root"
    exit 1
}

echo ""
log_info "=========================================="
log_info "All services are running!"
log_info "=========================================="
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
if [ "$NCA_AVAILABLE" = true ]; then
    echo "NCA Toolkit: http://localhost:8080"
else
    echo "NCA Toolkit: Not available (optional service)"
fi
log_info "=========================================="
log_info "Log files location: $LOG_DIR"
log_info "  - Main log: $MAIN_LOG"
log_info "  - Django log: $DJANGO_LOG"
log_info "  - React log: $REACT_LOG"
log_info "  - Error log: $ERROR_LOG"
log_info "  - Docker log: $DOCKER_LOG"
log_info "=========================================="
echo "Press Ctrl+C to stop all services."
echo ""

# Function to check process health and log status
check_process_health() {
    local pid=$1
    local name=$2
    if kill -0 $pid 2>/dev/null; then
        return 0
    else
        log_error "$name process (PID: $pid) has exited unexpectedly"
        return 1
    fi
}

# Function to monitor background tasks
monitor_background_tasks() {
    local iteration=0
    # Use exported PIDs or fall back to checking if they're set
    local django_pid=${DJANGO_PID:-0}
    local react_pid=${REACT_PID:-0}
    
    if [ "$django_pid" -eq 0 ] || [ "$react_pid" -eq 0 ]; then
        log_error "Monitor started before PIDs were set. Waiting..."
        sleep 5
        django_pid=${DJANGO_PID:-0}
        react_pid=${REACT_PID:-0}
        if [ "$django_pid" -eq 0 ] || [ "$react_pid" -eq 0 ]; then
            log_error "Monitor: PIDs still not available. Exiting monitor."
            return 1
        fi
    fi
    
    log_debug "Monitor: Tracking Django PID: $django_pid, React PID: $react_pid"
    
    while true; do
        sleep 30
        iteration=$((iteration + 1))
        
        # Refresh PIDs in case they changed
        django_pid=${DJANGO_PID:-$django_pid}
        react_pid=${REACT_PID:-$react_pid}
        
        # Check if main processes are still running
        if ! check_process_health $django_pid "Django"; then
            return 1
        fi
        if ! check_process_health $react_pid "React"; then
            return 1
        fi
        
        # Show periodic status every 60 seconds (visible to user)
        if [ $((iteration % 2)) -eq 0 ]; then
            echo "[$(date +'%H:%M:%S')] ✓ Services running (Django: $django_pid, React: $react_pid)"
        fi
        
        # Log detailed status to log file
        log_debug "Services running - Django (PID: $django_pid), React (PID: $react_pid)"
        
        # Check for transcription/processing processes
        STUCK_TRANSCRIPTION=$(ps aux | grep -E "(whisper|transcrib|ffmpeg.*audio|python.*transcribe)" | grep -v grep | wc -l | tr -d ' ')
        if [ "$STUCK_TRANSCRIPTION" -gt 0 ]; then
            log_debug "Background transcription/processing tasks detected: $STUCK_TRANSCRIPTION"
            # Show to user if transcription is running (every 2 minutes)
            if [ $((iteration % 4)) -eq 0 ]; then
                echo "[$(date +'%H:%M:%S')] 🔄 Transcription/processing active ($STUCK_TRANSCRIPTION process(es))"
            fi
        fi
        
        # Check Django log for recent errors (excluding normal API requests and expected errors)
        if [ -f "$DJANGO_LOG" ]; then
            RECENT_ERRORS=$(tail -200 "$DJANGO_LOG" | grep -iE "(error|exception|traceback|failed)" | grep -v "GET /api" | grep -v "POST /api" | grep -v "Broken pipe" | grep -v "must be transcribed" | tail -3)
            if [ ! -z "$RECENT_ERRORS" ]; then
                # Check if it's a critical error or just a user error
                CRITICAL_ERROR=$(echo "$RECENT_ERRORS" | grep -iE "(internal server|500|traceback|exception)" | head -1)
                if [ ! -z "$CRITICAL_ERROR" ]; then
                    log_warning "Recent Django errors detected (check $DJANGO_LOG for details)"
                    echo "[$(date +'%H:%M:%S')] ⚠️  Django errors detected - check logs: $DJANGO_LOG"
                fi
            fi
        fi
        
        # Check if ports are still listening
        if ! lsof -ti:$DJANGO_PORT &> /dev/null; then
            log_error "Django port $DJANGO_PORT is no longer listening!"
            return 1
        fi
        if ! lsof -ti:$REACT_PORT &> /dev/null; then
            log_warning "React port $REACT_PORT is no longer listening (may be normal if Vite is restarting)"
        fi
    done
}

# Kill any existing monitor processes from previous runs
pkill -f "monitor_background_tasks" 2>/dev/null || true
sleep 0.5

# Start background monitoring
# Export PIDs so the background function can access them
export DJANGO_PID REACT_PID DJANGO_PORT REACT_PORT DJANGO_LOG REACT_LOG
monitor_background_tasks &
MONITOR_PID=$!
log_debug "Started background monitor (PID: $MONITOR_PID)"

# Wait for processes with periodic status updates
log_info "Waiting for processes (Django PID: $DJANGO_PID, React PID: $REACT_PID)..."
log_info "Note: Script will continue running while services are active."
log_info "Status updates will appear every 60 seconds to confirm services are running."
log_info "If transcription appears stuck:"
log_info "  - Check Django logs: $DJANGO_LOG"
log_info "  - Check for background processes: ps aux | grep -E '(whisper|transcrib|ffmpeg)'"
log_info "  - Transcription can take several minutes for long videos"

# Wait for processes (this blocks until one exits)
wait $DJANGO_PID $REACT_PID
EXIT_CODE=$?

# Stop monitor
kill $MONITOR_PID 2>/dev/null || true

# Log which process exited
if ! kill -0 $DJANGO_PID 2>/dev/null; then
    log_error "Django process exited (code: $EXIT_CODE)"
    log_error "Check Django logs: $DJANGO_LOG"
fi

if ! kill -0 $REACT_PID 2>/dev/null; then
    log_error "React process exited (code: $EXIT_CODE)"
    log_error "Check React logs: $REACT_LOG"
fi

log_info "One or more services have stopped. Cleaning up..."
