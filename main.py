import pyperclip
import subprocess
from langdetect import detect
import torch
import soundfile as sf
from io import BytesIO
import numpy as np
import re
import os
import tkinter as tk
from tkinter import messagebox

# Мапа мов → (language, speaker alias)
VOICE_MAP = {
    "en": ("en", "v3_en"),       # англійська
    "ua": ("ua", "v4_ua"),       # українська
    "ru": ("ru", "ru_v3")        # російська
}

def detect_voice(text):
    try:
        lang = detect(text)
        if lang == "uk":   # langdetect повертає "uk", а Silero очікує "ua"
            lang = "ua"
        return VOICE_MAP.get(lang, ("en", "v3_en"))
    except:
        return ("en", "v3_en")

def split_into_chunks(text, max_len=800):
    """Розбиває текст на блоки по цілих реченнях"""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""

    for s in sentences:
        if len(current) + len(s) + 1 <= max_len:
            current += (" " + s if current else s)
        else:
            if current:
                chunks.append(current.strip())
            if len(s) > max_len:
                chunks.append(s.strip())  # довге речення окремо
                current = ""
            else:
                current = s
    if current:
        chunks.append(current.strip())
    return chunks

def show_message(title, text, is_error=False):
    """Показує системне повідомлення у вікні"""
    root = tk.Tk()
    root.withdraw()
    if is_error:
        messagebox.showerror(title, text)
    else:
        messagebox.showinfo(title, text)
    root.destroy()

def main():
    text = pyperclip.paste().strip()
    if not text:
        show_message("Помилка", "Буфер порожній", is_error=True)
        return

    language, default_speaker = detect_voice(text)

    # Завантажуємо Silero TTS модель
    model, example_texts = torch.hub.load(
        repo_or_dir='snakers4/silero-models',
        model='silero_tts',
        language=language,
        speaker=default_speaker
    )

    speaker = default_speaker if default_speaker in model.speakers else model.speakers[0]

    # Розбиваємо текст на блоки
    chunks = split_into_chunks(text, max_len=800)

    # Озвучуємо кожен блок
    audio_segments = []
    for chunk in chunks:
        audio = model.apply_tts(text=chunk, speaker=speaker, sample_rate=48000)
        audio_segments.append(audio)

    # Склеюємо у єдиний аудіопотік
    full_audio = np.concatenate(audio_segments)

    # Записуємо у BytesIO як WAV
    buffer = BytesIO()
    sf.write(buffer, full_audio, 48000, format="WAV")
    buffer.seek(0)

    # Шлях до вихідного файлу
    xdg_download = os.path.expanduser("~/Downloads")  # fallback
    config_file = os.path.expanduser("~/.config/user-dirs.dirs")
    
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            for line in f:
                if line.startswith("XDG_DOWNLOAD_DIR"):
                    path = line.split("=")[1].strip().strip('"')
                    xdg_download = os.path.expandvars(path)
    
    output_file = os.path.join(xdg_download, "111.mp3")
    if not os.path.exists(output_file):
        print("Файл буде створено:", output_file)

    # Використовуємо ffmpeg напряму для кодування у MP3
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", "pipe:0", "-f", "mp3", output_file],
        input=buffer.read(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if proc.returncode == 0:
        #show_message("Успіх", f"Збережено у {output_file} (голос: {speaker})")
        # VLC відтворює і закривається сам
        #subprocess.run(["cvlc", "--play-and-exit", output_file])
        subprocess.run([
            "mpv",
            "--no-terminal",
            "--really-quiet",
            "--no-video",
            output_file
        ])
    else:
        show_message("Помилка ffmpeg", proc.stderr.decode(), is_error=True)

if __name__ == "__main__":
    main()
