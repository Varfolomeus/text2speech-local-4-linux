# 🎙️ Text2Speech — Скрипт‑сенсей

A **Python-based Text-to-Speech (TTS)** application that uses **Silero neural voices** together with `ffmpeg` and `VLC`.  
This tool allows you to **convert any text from clipboard into natural-sounding speech** and save it as **MP3 audio files**.  
It is designed for **autonomous use**: one shortcut, one click — and your text is spoken aloud.

![ text2speech ](https://github.com/smoothcoode/Image/blob/main/tts.png?raw=true)

---

## ✨ Features

- 🎤 **Automatic Language Detection**  
  Supports English, Ukrainian, Russian voices.

- ⚡ **Smart Text Splitting**  
  Breaks long text into sentences for natural flow.

- 💾 **File Export**  
  Saves audio as `111.mp3` in `~/Downloads`.

- 🎧 **Autoplay with VLC**  
  Plays immediately and closes VLC after playback.

- 🖥️ **System Notifications**  
  Success and error messages shown via `tkinter` windows.

---

## 🛠️ Requirements

- **Python 3.9+**  
- **Linux desktop environment** (tested on Ubuntu)

### Required Packages:
- `torch`  
- `soundfile`  
- `langdetect`  
- `pyperclip`  
- `numpy`  
- `tkinter` (usually included with Python)  
- `ffmpeg`  
- `vlc`

> ⚠️ **Note:** Torch and models require several hundred MB.  
> Ensure you have enough **free disk space** before installation.

---

## 📦 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/Varfolomeus/text2speech-local-4-linux
   cd text2speech-local-4-linux
2. Create virtual environment:
 ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
3. Install dependencies:
  ```bash
  pip install torch soundfile langdetect pyperclip numpy
  sudo apt install ffmpeg vlc
  ```
4. Run the application:

 ```bash
 python main.py
 ```

🖥️ Desktop Integration
   ```bash
  cat > ~/.local/share/applications/text2speech.desktop << 'EOF'
  [Desktop Entry]
  Name=Text2Speech
  Comment=Speak text from clipboard
  Exec=/home/[yourusername]/text2speech/.venv/bin/python /home/[yourusername]/text2speech/main.py
  Icon=audio-volume-high
  Terminal=false
  Type=Application
  Categories=Utility;Audio;
  EOF
  ```
⌨️ Keyboard Shortcut
GNOME / Ubuntu
Open Settings → Keyboard → Shortcuts

Add new shortcut:
Name: Text2Speech
Command:
```bash
/home/[yourusername]/text2speech/.venv/bin/python /home/[yourusername]/text2speech/main.py
```
Key: Alt+K (or any other)

KDE / Plasma
Open System Settings → Shortcuts → Custom Shortcuts
Create new shortcut with the same command
Assign key Alt+K (or any other)

🚀 Usage
Copy any text to clipboard (Ctrl+C).
Press Alt+K (or run from menu).
Script‑sensei will:
  - Detect language
  - Split text into sentences
  - Generate speech
  - Save to 111.mp3
  - Play via CVLC and close after playback

