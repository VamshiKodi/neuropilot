# NeuroPilot – Autonomous AI Assistant

NeuroPilot is an advanced AI assistant designed to transform human-computer interaction through voice commands, autonomous task planning, and intelligent automation.

The system features a futuristic holographic interface inspired by Jarvis-style AI assistants.

Users can wake the assistant using the voice command **"Hey Neuro"** and interact with it naturally.

---

## 🚀 Features

• Voice wake-word activation ("Hey Neuro")  
• Autonomous AI task planning  
• Computer automation and control  

---

## ✨ Key Features

### 🧠 1. Autonomous Goal Mode
NeuroPilot can decompose high-level objectives (e.g., *"Help me prepare my research on space exploration"*) into structured action plans. It analyzes the goal, generates a plan, and executes it step-by-step.

### 🖥️ 2. Full Computer Control
Using `pyautogui`, NeuroPilot can type, press keys, and execute hotkeys. It can launch any application (Notepad, Chrome, VS Code) and perform complex tasks like setting up coding environments.

### 📁 3. Intelligent File Assistant
A robust file management system that allows the AI to create folders, move/rename files, and find documents across your workspace with built-in path protection.

### 🌐 4. Web Intelligence
Real-time web search integration with AI-powered summarization. NeuroPilot doesn't just give you links; it reads the results and provides a mission-style briefing.

### 🎙️ 5. Bi-Directional Voice & Wake Word
"Hey Neuro!" Activation. Use the Web Speech API for seamless voice input and high-quality Text-to-Speech (TTS) for AI replies.

### 📊 6. Holographic System Dashboard
Live telemetry panels surrounding a 3D robot background. Monitor CPU, RAM, Disk usage, and AI process logs in real-time with a futuristic HUD.

---

## 🛠️ Technical Stack

- **AI Engine:** Google Gemini 2.5 Flash (`google-genai`)
- **Backend:** Flask (Python 3.12)
- **Frontend:** Vanilla JS + CSS3 (Holographic HUD, 3D Sketchfab Integration)
- **Automation:** `pyautogui`, `subprocess`, `os`
- **System Monitoring:** `psutil`
- **Web Intelligence:** `BeautifulSoup4`, `requests`
- **Voice:** Web Speech API, `SpeechRecognition`

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.12 or higher
- A Google Gemini API Key ([Get one here](https://aistudio.google.com/app/apikey))

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/VamshiKodi/neuropilot.git
cd neuropilot

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### 4. Run the Mission
```bash
python app.py
```
Open `http://localhost:5000` in your browser.

---

## 🛡️ Security & Safety
- **Risk Confirmation Layer:** All "dangerous" actions (deleting files, typing on computer, sending emails) require explicit user confirmation via the UI.
- **Root Protection:** File operations are restricted to the project directory to prevent accidental system changes.
- **Offline Fallback:** Core automation (opening apps, system info) works even if the AI planning channel is unavailable.

---

## 🏆 Hackathon: Gemini Live Agent Challenge
This project was built specifically to showcase the reasoning and planning capabilities of the Gemini 2.5 Flash model in a local desktop environment.

- **The Challenge:** Building a "Live Agent" that can interact with the real world.
- **The Solution:** NeuroPilot bridges the gap between LLM reasoning and local system execution.

---

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Developed with ❤️ by [Vamshi Kodi](https://github.com/VamshiKodi)
