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
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python dependencies."
    exit 1
fi
echo "Python dependencies installed."
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
python3 manage.py runserver &
DJANGO_PID=$!
sleep 2
# Check if Django started successfully
if ! kill -0 $DJANGO_PID 2>/dev/null; then
    echo "Error: Django failed to start. Port $DJANGO_PORT may be in use."
    echo "Please stop the service using port $DJANGO_PORT and try again."
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
