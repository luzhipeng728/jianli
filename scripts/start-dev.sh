#!/bin/bash

# Development startup script for the Resume System
# This script starts all required services in the correct order

set -e

echo "=========================================="
echo "Starting Development Environment"
echo "=========================================="

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Step 1: Start Docker Compose services (Elasticsearch & Redis)
echo ""
echo "[1/5] Starting Docker services (Elasticsearch & Redis)..."
docker compose up -d

# Step 2: Wait for Elasticsearch to be ready
echo ""
echo "[2/5] Waiting for Elasticsearch to be ready..."
echo "This may take a minute..."

max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:9200/_cluster/health >/dev/null 2>&1; then
        echo "Elasticsearch is ready!"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo ""
    echo "ERROR: Elasticsearch failed to start within the expected time"
    exit 1
fi

# Step 3: Initialize Elasticsearch indices
echo ""
echo "[3/5] Initializing Elasticsearch indices..."
python3 "$PROJECT_ROOT/backend/scripts/init_es.py"

# Step 4: Start Backend (FastAPI with uvicorn)
echo ""
echo "[4/5] Starting Backend (FastAPI)..."
cd "$PROJECT_ROOT/backend"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Wait a moment for backend to start
sleep 3

# Step 5: Start Frontend (Vite dev server)
echo ""
echo "[5/5] Starting Frontend (Vite)..."
cd "$PROJECT_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

# Completion message
echo ""
echo "=========================================="
echo "Development Environment Started!"
echo "=========================================="
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Elasticsearch: http://localhost:9200"
echo "Redis: localhost:6379"
echo ""
echo "Press Ctrl+C to stop all services"
echo "=========================================="

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "=========================================="
    echo "Shutting down services..."
    echo "=========================================="

    # Kill backend and frontend processes
    if [ ! -z "$BACKEND_PID" ]; then
        echo "Stopping Backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || true
    fi

    if [ ! -z "$FRONTEND_PID" ]; then
        echo "Stopping Frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null || true
    fi

    # Stop Docker services
    echo "Stopping Docker services..."
    cd "$PROJECT_ROOT"
    docker compose down

    echo "All services stopped."
    exit 0
}

# Trap Ctrl+C and other termination signals
trap cleanup SIGINT SIGTERM

# Wait for background processes
wait
