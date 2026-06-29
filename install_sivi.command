#!/bin/bash

# Ensure script runs from its own directory
cd "$(dirname "$0")"

echo "================================================"
echo " SIVI AI Installer (macOS)"
echo "================================================"
echo ""

echo "[1/4] Checking prerequisites..."
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed! Please install Python3."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "Node.js/npm is not installed! Please install Node.js."
    exit 1
fi

echo "Checking for portaudio (required for voice)..."
if ! brew ls --versions portaudio > /dev/null; then
    if ! command -v brew &> /dev/null; then
        echo "Homebrew is missing! Please install it from https://brew.sh/ to get portaudio."
        exit 1
    fi
    echo "Installing portaudio via Homebrew..."
    brew install portaudio
fi

echo "[2/4] Setting up Python virtual environment..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
cd ..

echo "[3/4] Installing Frontend dependencies..."
cd frontend
npm install
cd ..

echo "[4/4] Creating Desktop Alias..."
# macOS way to create a shortcut: An AppleScript that makes an alias
osascript -e "tell application \"Finder\" to make alias file to POSIX file \"$(pwd)/start_sivi.command\" at desktop"
# Rename the alias to "SIVI AI"
osascript -e "tell application \"Finder\" to set name of file \"start_sivi.command alias\" of desktop to \"SIVI AI\"" 2>/dev/null || true

# Make launchers executable
chmod +x start_sivi.command
chmod +x start_silent.sh

echo ""
echo "================================================"
echo " Setup Complete! "
echo " You can now launch SIVI AI from your desktop. "
echo "================================================"
