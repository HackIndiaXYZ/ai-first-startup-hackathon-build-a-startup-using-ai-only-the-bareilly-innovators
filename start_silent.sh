#!/bin/bash
cd "$(dirname "$0")"

echo "Killing old node and python processes..."
pkill -f "node" 2>/dev/null
pkill -f "bridge_server.py" 2>/dev/null
pkill -f "Wake_Word_detection.py" 2>/dev/null
pkill -f "background_monitor.py" 2>/dev/null

sleep 2

echo "Starting Bridge Server..."
(cd backend && source venv/bin/activate && python bridge_server.py &> /dev/null &)

echo "Waiting for backend to initialize..."
sleep 3

echo "Starting Wake Word Listener..."
(cd backend && source venv/bin/activate && python core/Wake_Word_detection.py &> /dev/null &)

echo "Starting Background Monitor..."
(cd backend && source venv/bin/activate && python core/background_monitor.py &> /dev/null &)

echo "Starting Frontend Dashboard..."
(cd frontend && npm run dev &> /dev/null &)

echo "All services started in background!"
