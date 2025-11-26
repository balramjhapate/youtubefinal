#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo "Stopping servers..."
    kill $DJANGO_PID
    kill $REACT_PID
    echo "Stopping NCA Toolkit..."
    docker stop nca-toolkit
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

# Start Django Backend
echo "Starting Django Backend..."
cd backend
python3 manage.py runserver &
DJANGO_PID=$!
cd ..

# Start React Frontend
echo "Starting React Frontend..."
cd frontend
npm run dev -- --host &
REACT_PID=$!
cd ..

echo "All services are running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "NCA Toolkit: http://localhost:8080"
echo "Press Ctrl+C to stop."

# Wait for processes
wait $DJANGO_PID $REACT_PID
