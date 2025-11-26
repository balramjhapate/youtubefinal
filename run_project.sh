#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo "Stopping servers..."
    kill $DJANGO_PID
    kill $REACT_PID
    exit
}

# Trap SIGINT (Ctrl+C)
trap cleanup SIGINT

echo "Starting RedNote Project..."

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

echo "Both servers are running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop."

# Wait for processes
wait $DJANGO_PID $REACT_PID
