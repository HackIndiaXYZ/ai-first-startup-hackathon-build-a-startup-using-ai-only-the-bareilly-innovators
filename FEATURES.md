# 🤖 SIVI AI (Sivi) — Comprehensive Feature & Command Guide

This document is the **Ultimate Single Source of Truth** for the SIVI AI (Sivi) Voice Assistant. It deeply lists every single capability, module, and exact working voice/text command that the system understands and executes natively as of the latest Gemini Multi-Key / Vector Memory architecture.

Sivi works best with **Hinglish (Hindi + English mix)** and raw English. You can speak to her as naturally as you would to a human.

---

## 💻 1. System & Hardware Control
Control your core Windows operating system components directly via voice.

| Feature | Description | Voice / Text Commands (Examples) |
|---|---|---|
| **Volume Control** | Adjust PC audio volume dynamically. | *"Volume up"*<br>*"Volume badha do"*<br>*"Set volume to 70"*<br>*"Mute the volume"* |
| **Brightness Control** | Adjust screen brightness. | *"Brightness up"*<br>*"Make the screen dimmer"*<br>*"Brightness kam karo"* |
| **Power Management** | Lock, restart, sleep, or shutdown. | *"Lock the screen"*<br>*"Put the computer to sleep"*<br>*"Restart the PC"*<br>*"Shutdown the computer"* |
| **Connectivity** | Toggle network radios. | *"Turn on WiFi"*<br>*"Disable Bluetooth"* |
| **System Diagnostics** | Check battery, time, and PC health. | *"What is the system status?"*<br>*"Check battery"*<br>*"Time kya ho raha hai"* |

---

## 🪟 2. Application & Window Management
Open apps, manipulate windows, and arrange your workspace.

| Feature | Description | Voice / Text Commands (Examples) |
|---|---|---|
| **App Launcher** | Opens any installed application. | *"Open Chrome"*<br>*"Start Notepad"*<br>*"Visual Studio Code kholo"* |
| **Window State** | Maximize, minimize, or close apps. | *"Minimize window"*<br>*"Maximize window"*<br>*"Close Chrome"* |
| **Window Snapping** | Organize windows to left/right for multitasking. | *"Snap to left"*<br>*"Snap to right"* |
| **Window Switching** | Switch focus between running apps. | *"Switch to Telegram"*<br>*"Go to WhatsApp"* |
| **Active Windows** | Read aloud all currently open applications. | *"What apps are open?"*<br>*"Read active windows"* |

---

## 🌐 3. Advanced Browser & Media Control
Control your browser, tabs, and media playback completely hands-free.

| Feature | Description | Voice / Text Commands (Examples) |
|---|---|---|
| **Tab Management** | Navigate, create, or close browser tabs. | *"Next tab"*<br>*"Previous tab"*<br>*"Close tab"*<br>*"Open a new tab"* |
| **Page Navigation** | Scroll and read the active webpage. | *"Scroll down"*<br>*"Scroll up"*<br>*"Read this page"* |
| **Web Search** | Instantly search Google. | *"Search for latest AI news"*<br>*"Google weather in Delhi"* |
| **Media Playback** | Control system media (Play, Pause, Next). | *"Play music"*<br>*"Next track"*<br>*"Pause video"* |
| **YouTube** | Instantly search and play YouTube videos. | *"Play Linkin Park on YouTube"*<br>*"Play LoFi study beats"* |

---

## 🧠 4. Intelligence, Memory & Agents
Sivi's core intelligence, featuring Vector Memory (ChromaDB), RAG, and Background Agents.

| Feature | Description | Voice / Text Commands (Examples) |
|---|---|---|
| **Vector Memory** | Tell Sivi facts to remember permanently. | *"Remember that my favorite color is crimson"*<br>*"Memorize that I like Python"* |
| **Memory Recall** | Sivi uses memory to answer personal queries. | *"What is my favorite color?"*<br>*"Do you remember my dog's name?"* |
| **RAG Document Search** | Ask deep questions about local PDFs/MDs. | *"Search my documents for the API keys"*<br>*"Read my files and summarize them"* |
| **Background Orchestrator**| Complex tasks are offloaded to agents automatically without blocking UI. | *"Analyze the code in main.py"*<br>*"Debug this error for me"* |
| **Always-On Polling** | Sivi polls HackerNews every 2 hours and speaks out loud if a story matches your interests. | *(Autonomous / No manual command needed)* |

---

## 📱 5. WhatsApp Desktop Automation
Automate WhatsApp Desktop UI to send messages and make calls.

| Feature | Description | Voice / Text Commands (Examples) |
|---|---|---|
| **Send Messages** | Type and send WhatsApp messages. | *"Send message to Rahul saying I am late"*<br>*"WhatsApp karo Mom ko saying coming"* |
| **Read Chats** | Read unread messages from a contact. | *"Read messages from Rahul"*<br>*"Read WhatsApp"* |
| **Make Calls** | Initiate Voice or Video calls. | *"Voice call Rahul on WhatsApp"*<br>*"Video call Mom on WhatsApp"* |
| **Send Media/Voice Notes**| Send files or record voice notes. | *"Send document report.pdf to Rahul"*<br>*"Send voice note to Mom"* |

---

## 🛠️ 6. Developer & IT Operations
Superpower your coding workflow with local developer tools.

| Feature | Description | Voice / Text Commands (Examples) |
|---|---|---|
| **Command Line Execution**| Run raw terminal commands. | *"Run command git status"*<br>*"Run command npm install"* |
| **Port Management** | Kill hanging local development ports. | *"Kill port 3000"* |
| **Code Generation** | Write AI code directly to a file. | *"Generate a python script to sort files in output.py"* |
| **Code Analysis** | Have the AI deeply analyze a local file. | *"Analyze code in backend.py"* |
| **Editor Control** | Open or close files in your editor (VS Code). | *"Open file config.json in editor"*<br>*"Close the editor"* |

---

## 🧩 7. Plugins & MCP (Model Context Protocol)
Extensible tool execution.

| Feature | Description | Voice / Text Commands (Examples) |
|---|---|---|
| **Weather Plugin** | Live weather data via wttr.in. | *"Weather in Delhi"*<br>*"What's the weather in Mumbai?"* |
| **Todo Plugin** | Manage a local task list. | *"Add buy groceries to my todo list"*<br>*"Read my todo list"*<br>*"Clear my todo list"* |
| **MCP Router** | Sivi can execute tools on registered MCP stdio servers. | *(Handled autonomously by Sivi's AI when you request complex file/git operations).* |

---

## 👁️ 8. Computer Vision & Hardware Interaction
Leverage your webcam and screen reading capabilities.

| Feature | Description | Voice / Text Commands (Examples) |
|---|---|---|
| **Screen Reading (OCR)** | Extract and summarize text visible on screen. | *"Read my screen"*<br>*"What is on my screen?"* |
| **Screenshot Capture** | Takes and saves a screenshot instantly. | *"Take a screenshot"*<br>*"Screen capture le lo"* |
| **Emotion Analysis** | Analyzes your face via Webcam (if enabled). | *"How do I look?"*<br>*"Check my mood"* |
| **Scene Description** | Takes a photo and describes your environment. | *"What do you see?"*<br>*"Describe the scene"* |

---

## ⌨️ 9. Keyboard & Mouse Emulation
Low-level simulated inputs for anything that lacks a direct API.

| Feature | Description | Voice / Text Commands (Examples) |
|---|---|---|
| **Keyboard Typing** | Types exact text on the screen. | *"Type hello world"*<br>*"Likho I am busy"* |
| **Keystrokes** | Presses specific keys (Enter, Tab, etc.) | *"Press enter"*<br>*"Press tab"* |
| **Mouse Clicking** | Clicks at current cursor position. | *"Mouse click"*<br>*"Double click"* |
| **Mouse Movement** | Moves cursor in a direction. | *"Move mouse up"*<br>*"Move mouse left"* |

---

## 📊 10. Smart Briefings Dashboard (UI)
Sivi comes with a deeply responsive React + Vite web dashboard.

| Feature | Description | Voice / Text Commands (Examples) |
|---|---|---|
| **Live Weather & Location** | Real-time weather widget powered by `wttr.in`. | *(Auto-updates on dashboard)* |
| **System Health & Network** | Live monitoring of Battery %, CPU %, and Network Speed. | *(Auto-updates on dashboard)* |
| **Today's Schedule** | Pulls and displays today's events from Google Calendar. | *(Auto-updates on dashboard)* |
| **Live News Feed** | Scrolling feed of the latest important headlines. | *(Auto-updates on dashboard)* |
| **Responsive Design** | Fully optimized for Desktop, Tablet, and Mobile with icon-only navigation. | *(UI feature)* |

---

## 🔄 11. Multi-Command Workflows (Macros)
Sivi can execute multiple commands back-to-back in a single sentence.

| Command Pattern | Example Response |
|---|---|
| **Sequential Execution** | *"Mute the volume and lock the screen"* <br>→ *(Executes Mute, then executes Lock)* |
| **Macro Routines** | *"Run my morning routine"* <br>→ *(Executes Spotify Play, reads Weather, reads Todo list)* |

---
*Generated by SIVI Architecture.*

# Sivi 3.0: Advanced Human-Like Intelligence Features

Sivi has been significantly upgraded from a standard voice assistant to an autonomous, emotionally aware AI companion. Here are the core features of the Sivi 3.0 Intelligence Architecture:

## 1. Autonomous Sensory Empathy
Sivi acts like a real companion by observing you silently. She will periodically check your webcam (every 15 minutes) and system state in the background. If she notices signs of extreme fatigue (rubbing eyes, poor posture), she will **spontaneously initiate a conversation** to ask if you are okay and suggest a break, without you needing to say a word.

## 2. The Subconscious (Implicit Memory)
You no longer need to explicitly say "Remember X". Sivi silently listens to your general conversations, extracts your habits, preferences, and recurring issues, and stores them in her Subconscious Memory (ChromaDB). She will naturally bring up these facts in future conversations.

## 3. Graceful Interruption Handling
Like a human, Sivi understands when you interrupt her. If you speak loudly while she is talking, she will immediately stop her audio playback and ask, "Sorry, aap kuch keh rahe the?" (Sorry, were you saying something?).

## 4. Temporal Emotional Drift
Sivi doesn't just read your current emotion—she remembers how you've been feeling over the past few days. If you've been stressed for three days straight, her baseline personality will temporarily shift to be softer and more supportive. If you've been happy, she will remain energetic and playful.

## 5. Swarm Intelligence (Multi-Agent Routing)
For complex, multi-step queries (e.g., "Plan my weekend"), Sivi will act as a Manager and spawn parallel sub-agents (e.g., a Search Agent and a Planning Agent). She will compile their findings in the background and present you with a synthesized answer.
