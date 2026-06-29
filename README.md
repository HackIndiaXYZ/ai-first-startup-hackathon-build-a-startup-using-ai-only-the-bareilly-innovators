# 🌌 SIVI / Sivi AI Voice Assistant

A powerful, ultra-responsive, real-time Voice AI Assistant built for Windows PC. SIVI (Sivi) leverages the **Google Gemini Live API (Native Audio via WebSockets)** to provide instantaneous, human-like voice conversations, system control, and visual intelligence.

## ✨ Key Features

- **🗣️ Real-time Native Audio:** Lightning-fast, natural conversation powered by Gemini 2.5 Flash Native Audio.
- **💻 Deep PC Integration:** Control your Windows PC completely via voice. Open apps, manage windows, control volume, type text, and manage files.
- **👀 AI Vision & Screen Reading:** Sivi can look through your webcam to analyze your mood, read your screen, or take photos.
- **🎭 4 Dynamic Personalities:** Switch on the fly between *GF Mode 💖*, *Professional Mode 💼*, *Assistant Mode 🤖*, and *Developer Mode 💻*.
- **🌐 Bilingual (Hinglish/English):** Seamlessly understands and speaks a natural mix of Hindi and English.
- **🔌 Extensible Plugin System:** Includes built-in plugins for Live Weather, Calculator, Google News, Spotify, and Google Calendar.
- **⚡ Smart Briefings Dashboard:** A deeply responsive, beautiful React + Vite frontend dashboard that dynamically renders real-time weather, system health, internet speeds, live news, and your daily schedule.

---

## 🛠️ Architecture

- **Backend:** Python, FastAPI, WebSockets (`bridge_server.py`)
- **Frontend:** React, Vite (`npm run dev`)
- **Audio Engine:** `sounddevice` (PCM 16-bit, 16kHz Mic Input, 24kHz Speaker Output)
- **AI Brain:** `google-genai` (BidiGenerateContent WebSocket)

---

## 🚀 Installation & Setup

### 1. Prerequisites
- Python 3.10+
- Node.js (for the frontend)
- A Google Gemini API Key

### 2. Backend Setup
Navigate to the `backend` folder and install dependencies:
```bash
cd backend
pip install -r requirements.txt

# Install extra integrations
pip install spotipy google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 3. Frontend Setup
Navigate to the `frontend` folder and install NPM packages:
```bash
cd frontend
npm install
```

### 4. Configuration
Create a `.env` file in the `backend` directory and configure your keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
# Optional Integrations
SPOTIPY_CLIENT_ID=your_spotify_id
SPOTIPY_CLIENT_SECRET=your_spotify_secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
```
*Note for Google Calendar:* Place your `credentials.json` from the Google Cloud Console in the root `backend` directory.

---

## 🏃‍♂️ Running the Assistant

**Easiest Way (Windows):**
Simply double-click the **`start_sivi.bat`** file located in the root directory. 
This smart script will automatically:
1. Search for and terminate any lingering or frozen SIVI processes from your last session.
2. Free up ports 8000 and 5173 to prevent socket bind errors.
3. Launch the Backend, Wake Word Listener, and Frontend in clean, separate windows.

**Manual Way:**
You need to start both the backend bridge server and the frontend UI.

**1. Start the Backend API (Port 8000)**
```bash
cd backend
python bridge_server.py
```

**2. Start the Frontend UI (Port 5173)**
```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser. Enter your API key in the settings (if you haven't already), hit **Start Sivi**, and start speaking!

---

## 🧠 System Commands Example

You can speak naturally to Sivi. Here are some examples of what she can do:
- *"Open Chrome and search for Python tutorials."*
- *"Volume ko thoda badha do."*
- *"Take a photo, how am I looking today?"*
- *"Sivi, switch to developer mode."*
- *"Create a file named report.txt on my desktop."*
- *"What are the top news headlines?"*

---

## 📂 Project Structure

- `backend/core/`: Contains the core logic (Audio Engine, Command Parser, LLM API, Window/System Controllers).
- `backend/plugins/`: Modular system for adding new capabilities.
- `backend/bridge_server.py`: FastAPI server that bridges the Frontend UI with the PC's operating system and Gemini Live.
- `backend/test_integration.py`: Massive 120+ test suite ensuring all modules are functioning properly.
- `frontend/`: The React web interface.

---

*Built with ❤️ for advanced agentic PC control.*
