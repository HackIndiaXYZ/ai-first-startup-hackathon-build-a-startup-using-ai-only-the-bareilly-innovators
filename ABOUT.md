# Sivi AI – Autonomous Voice Intelligence System

Sivi is a highly advanced, low-latency, and autonomous Voice AI system designed specifically for the Windows OS ecosystem. Operating via the Gemini 2.5 Flash Native Audio Live API, Sivi processes raw PCM audio directly via WebSockets to enable true "Human-like" conversational pacing, real-time interruption, and deep system-level execution.

---

## 🌟 Core Architecture

Sivi is split into a robust Python backend and a lightweight, visually stunning React frontend.

### 🖥️ The Frontend (React + Vite)
- **Glassmorphism UI:** A sleek, dark-mode, highly optimized UI with responsive panels, dynamic overlays, and floating layout components. Built using pure React, resulting in an exceptionally small footprint.
- **3D Particle Nexus (`particles.html`):** A custom-built, hardware-accelerated Three.js 3D sphere consisting of 8,000 vertices. This sphere serves as Sivi's "Brain" visualization. It listens to the live WebSocket `amplitude` stream to dynamically scale, vibrate, and "bubble" in perfect sync with real-time audio volume from both the user's microphone and Sivi's generated voice. 
- **Unified Deployment:** The frontend is statically compiled using Vite into a `dist/` folder and served directly by the Python backend on `http://localhost:8000`, eliminating the need for a separate Node dev server. This simplifies the user experience into a single-click startup.

### ⚙️ The Backend (Python + FastAPI)
- **`bridge_server.py`:** The heart of the system. Runs a high-performance FastAPI Uvicorn server handling WebSocket streaming (`/ws`), API endpoints (`/settings`, `/voice/stop`), and serving the static React frontend. It manages the asynchronous threads routing audio bytes to the Gemini Live Client.
- **`audio_engine.py`:** Manages ultra-low latency PCM hardware capture via `sounddevice` with `pyaudio` fallback. Features a **Soft Noise Gate** that mathematically mutes (`\x00`) background fan noise/static to prevent API hallucinations, and an **Echo Suppression Hysteresis** to gracefully turn off the mic when Sivi is speaking, preventing hardware loops.
- **`gemini_live_client.py`:** A bidirectional WebSocket client that establishes the connection to Google's Generative AI. It manages session state, parses incoming JSON audio buffers, routes system commands securely, and keeps the connection alive using 8-second silent PCM injection chunks to bypass inactivity timeouts.

---

## 🧠 Autonomous Capabilities (Core Modules)

Sivi doesn't just talk; she controls the host machine via her robust plugin architecture. When she decides to execute a system command based on user intent, she triggers specialized local Python controllers:

### 🛠️ Hardware & OS Integration
*   **`system_controller.py` & `app_launcher.py`:** Controls volume, toggles screen brightness, locks the PC, and natively launches applications using `os.startfile`. If an app isn't found in the Windows Registry, Sivi gracefully falls back to a PyAutoGUI macro to physically open the Windows Start Menu, type the app name, and launch it natively.
*   **`camera_vision.py`:** Utilizes `cv2.CAP_DSHOW` (DirectShow backend) to take ultra-fast, unblockable webcam snapshots. This avoids thread-locks and allows Sivi to analyze the user's surroundings or detect emotions natively via Gemini Vision APIs instantly.
*   **`window_manager.py` & `screen_reader.py`:** Gives Sivi eyes on the operating system. She can capture the active screen, parse bounding boxes, extract text via OCR, and summarize visible documents or web pages.
*   **`mouse_controller.py` & `keyboard_controller.py`:** Bestows true RPA (Robotic Process Automation) capabilities upon Sivi. She can move the mouse, scroll, click, and type on behalf of the user based entirely on conversational voice commands.

### 🌐 Digital Life Integration
*   **`calendar_manager.py`:** Connects to scheduling systems to manage the user's day.
*   **`spotify_controller.py`:** Integrates with local media players to handle music playback, skipping tracks, and adjusting media volume seamlessly.
*   **`jarvis_email.py` & `gnews.py`:** Can autonomously draft emails or fetch the latest breaking news.

---

## 🔁 Persistent Memory & Self-Healing

- **`sivi_chat_history.json`:** Sivi maintains a rolling memory of the last 48 hours of conversation (capped at 200 items). This ensures context is maintained seamlessly across computer reboots, allowing the user to say "What were we talking about yesterday?" and receive an accurate answer.
- **Self-Healing Error Loop:** Sivi features a powerful recursive error-catching loop. If a local system command throws an error (e.g. failing to open a file or typing an incorrect command syntax), the Python backend catches the Python traceback and sends it *back* to Sivi internally via the WebSocket. Sivi reads her own error, diagnoses the issue, and autonomously attempts to write a new command to fix it without user intervention.
- **Config Management (`sivi_settings.json`):** A centralized source of truth for all user preferences, API keys, and voice tuning parameters, dynamically loaded on startup.

---

## 🚀 How to Run

1. Navigate to the TITAN backend directory:
   ```cmd
   cd c:\Users\Harikesn\Desktop\TITAN\backend
   ```
2. Activate your virtual environment (if applicable) and start the unified server:
   ```cmd
   python bridge_server.py
   ```
3. The server will host both the backend API and the frontend UI automatically. Open your browser to:
   **`http://localhost:8000`**
