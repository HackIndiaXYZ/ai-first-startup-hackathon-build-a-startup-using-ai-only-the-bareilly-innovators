#!/bin/bash
cd "$(dirname "$0")"

echo "  ███████╗██╗██╗   ██╗██╗"
echo "  ██╔════╝██║██║   ██║██║"
echo "  ███████╗██║██║   ██║██║"
echo "  ╚════██║██║╚██╗ ██╔╝██║"
echo "  ███████║██║ ╚████╔╝ ██║"
echo "  ╚══════╝╚═╝  ╚═══╝  ╚═╝"
echo ""
echo "  Advanced Voice Assistant System"
echo "  ================================================"
echo ""

echo "[1/4] Freeing Port 8000 (Backend Bridge Server)..."
lsof -ti:8000 | xargs kill -9 2>/dev/null

echo "[2/4] Freeing Port 5173 (Frontend Dashboard)..."
lsof -ti:5173 | xargs kill -9 2>/dev/null

echo "[3/4] Killing old Node.js processes..."
pkill -f "node" 2>/dev/null

echo "[4/4] Killing lingering Python processes..."
pkill -f "bridge_server.py" 2>/dev/null
pkill -f "Wake_Word_detection.py" 2>/dev/null
pkill -f "background_monitor.py" 2>/dev/null

echo ""
echo "Waiting 2 seconds for ports to clear..."
sleep 2

echo ""
echo "================================================"
echo " Launching SIVI AI Services"
echo "================================================"
echo ""

echo "Starting Backend Bridge Server (Port 8000)..."
osascript -e "tell application \"Terminal\" to do script \"cd '$(pwd)/backend' && source venv/bin/activate && python bridge_server.py\""

echo "Waiting for backend to initialize..."
sleep 5

echo "Starting Wake Word Listener..."
osascript -e "tell application \"Terminal\" to do script \"cd '$(pwd)/backend' && source venv/bin/activate && python core/Wake_Word_detection.py\""

echo "Starting Proactive Background Monitor..."
osascript -e "tell application \"Terminal\" to do script \"cd '$(pwd)/backend' && source venv/bin/activate && python core/background_monitor.py\""

echo "Starting Frontend Dashboard (Port 5173)..."
osascript -e "tell application \"Terminal\" to do script \"cd '$(pwd)/frontend' && npm run dev\""

echo ""
echo "================================================"
echo "  All systems GO!"
echo "  Dashboard: http://localhost:5173"
echo "  API:       http://localhost:8000"
echo "  Docs:      http://localhost:8000/docs"
echo "================================================"
echo ""
