import pyperclip
import subprocess
from langdetect import detect
import torch
import soundfile as sf
from io import BytesIO
import numpy as np
import re
import os
import datetime
import tkinter as tk
from tkinter import messagebox
from num2words import num2words

# Мапа мов → (silero_language, silero_speaker)
VOICE_MAP = {
    "en": ("en", "v3_en"),
    "uk": ("ua", "v4_ua"),
    "ru": ("ru", "ru_v3"),
    "fr": ("fr", "v3_fr"),
    "de": ("de", "v3_de"),
    "es": ("es", "v3_es")
}

# Глобальна змінна для детектованої мови
detected_lang = None

def detect_voice(text):
    global detected_lang
    try:
        detected_lang = detect(text)
        return VOICE_MAP.get(detected_lang, ("en", "v3_en"))
    except:
        detected_lang = "en"
        return ("en", "v3_en")

def normalize_numbers(text):
    """Перетворює числа (цілі та з дробовою частиною) на слова"""
    num_lang = detected_lang
    
    def replacer(match):
        num_str = match.group()
        # Дробові числа (14.5 або 45%)
        if "." in num_str or "," in num_str:
            parts = re.split(r"[.,]", num_str)
            try:
                whole = num2words(int(parts[0]), lang=num_lang)
                frac = " ".join([num2words(int(d), lang=num_lang) for d in parts[1]])
                if "%" in num_str:
                    return f"{whole} кома {frac} відсотків" if num_lang == "uk" else f"{whole} point {frac} percent"
                return f"{whole} кома {frac}" if num_lang == "uk" else f"{whole} point {frac}"
            except Exception:
                return num_str
        # Відсотки (45%)
        elif "%" in num_str:
            try:
                num = int(num_str.replace("%", ""))
                words = num2words(num, lang=num_lang)
                return f"{words} відсотків" if num_lang == "uk" else f"{words} percent"
            except Exception:
                return num_str
        # Цілі числа
        else:
            try:
                return num2words(int(num_str), lang=num_lang)
            except Exception:
                # Якщо не вдалося - по цифрі
                return " ".join(list(num_str))
    
    return re.sub(r"\d+[.,]?\d*%?", replacer, text)

def normalize_dates(text):
    """Перетворює дати формату YYYY-MM-DD або DD.MM.YYYY"""
    date_lang = detected_lang
    
    def replacer(match):
        date_str = match.group()
        try:
            for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]:
                try:
                    date = datetime.datetime.strptime(date_str, fmt).date()
                    if date_lang == "uk":
                        months_ua = ["січня", "лютого", "березня", "квітня", "травня", "червня",
                                   "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"]
                        return f"{date.day} {months_ua[date.month-1]} {date.year} року"
                    elif date_lang == "ru":
                        return date.strftime("%d %B %Y года")
                    else:
                        return date.strftime("%B %d, %Y")
                except ValueError:
                    continue
        except Exception:
            pass
        return date_str
    
    return re.sub(r"\d{4}-\d{2}-\d{2}|\d{2}[./]\d{2}[./]\d{4}", replacer, text)

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
                chunks.append(s.strip())
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

def get_download_dir():
    """Отримує шлях до Downloads через XDG"""
    xdg_download = os.path.expanduser("~/Downloads")
    config_file = os.path.expanduser("~/.config/user-dirs.dirs")
    
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            for line in f:
                if line.startswith("XDG_DOWNLOAD_DIR"):
                    path = line.split("=")[1].strip().strip('"')
                    xdg_download = os.path.expandvars(path)
    return xdg_download

def main():
    text = pyperclip.paste().strip()
    if not text:
        show_message("Помилка", "Буфер порожній", is_error=True)
        return

    language, default_speaker = detect_voice(text)
    
    # Нормалізація чисел
    if re.search(r"\d", text):
        text = normalize_numbers(text)
    
    # Нормалізація дат
    if re.search(r"\d{4}-\d{2}-\d{2}|\d{2}[./]\d{2}[./]\d{4}", text):
        text = normalize_dates(text)

    # Завантажуємо Silero TTS модель
    try:
        model, example_texts = torch.hub.load(
            repo_or_dir='snakers4/silero-models',
            model='silero_tts',
            language=language,
            speaker=default_speaker
        )
    except Exception as e:
        show_message("Помилка", f"Не вдалося завантажити модель для мови '{detected_lang}'", is_error=True)
        return

    # Вибір спікера
    if hasattr(model, 'speakers'):
        speaker = default_speaker if default_speaker in model.speakers else model.speakers[0]
        print(f"Спікер: {speaker} | Мова: {detected_lang} → {language}")
    else:
        show_message("Помилка", f"Мова '{detected_lang}' не підтримується Silero TTS", is_error=True)
        return

    # Розбиваємо текст на блоки
    chunks = split_into_chunks(text, max_len=800)

    # Озвучуємо кожен блок
    audio_segments = []
    for idx, chunk in enumerate(chunks, 1):
        audio = model.apply_tts(text=chunk, speaker=speaker, sample_rate=48000)
        audio_segments.append(audio)

    # Склеюємо у єдиний аудіопотік
    full_audio = np.concatenate(audio_segments)

    # Записуємо у BytesIO як WAV
    buffer = BytesIO()
    sf.write(buffer, full_audio, 48000, format="WAV")
    buffer.seek(0)

    # Шлях до вихідного файлу
    output_file = os.path.join(get_download_dir(), "111.mp3")

    # Кодування у MP3
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", "pipe:0", "-f", "mp3", output_file],
        input=buffer.read(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if proc.returncode == 0:
        subprocess.run(["mpv", "--no-terminal", "--really-quiet", "--no-video", output_file])
    else:
        show_message("Помилка ffmpeg", proc.stderr.decode(), is_error=True)

if __name__ == "__main__":
    main()
