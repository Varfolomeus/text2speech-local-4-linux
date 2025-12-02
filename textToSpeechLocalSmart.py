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

# ============================================================
# Словники назв літер (латиниця)
# ============================================================
LETTER_NAMES_US = {
    "A":"ay","B":"bee","C":"cee","D":"dee","E":"ee","F":"ef","G":"gee","H":"aitch",
    "I":"eye","J":"jay","K":"kay","L":"el","M":"em","N":"en","O":"oh","P":"pee",
    "Q":"cue","R":"ar","S":"ess","T":"tee","U":"you","V":"vee","W":"double-you",
    "X":"ex","Y":"why","Z":"zee"
}
LETTER_NAMES_FR = {
    "A":"a","B":"be","C":"ce","D":"de","E":"e","F":"effe","G":"ge","H":"ache",
    "I":"i","J":"ji","K":"ka","L":"elle","M":"emme","N":"enne","O":"o","P":"pe",
    "Q":"ku","R":"erre","S":"esse","T":"te","U":"u","V":"ve","W":"double ve",
    "X":"ix","Y":"i grec","Z":"zede"
}
LETTER_NAMES_DE = {
    "A":"a","B":"be","C":"ce","D":"de","E":"e","F":"ef","G":"ge","H":"ha",
    "I":"i","J":"jot","K":"ka","L":"el","M":"em","N":"en","O":"o","P":"pe",
    "Q":"ku","R":"er","S":"es","T":"te","U":"u","V":"vau","W":"we","X":"iks",
    "Y":"ypsilon","Z":"zet"
}
LETTER_NAMES_ES = {
    "A":"a","B":"be","C":"ce","D":"de","E":"e","F":"efe","G":"ge","H":"hache",
    "I":"i","J":"jota","K":"ka","L":"ele","M":"eme","N":"ene","O":"o","P":"pe",
    "Q":"cu","R":"erre","S":"ese","T":"te","U":"u","V":"uve","W":"uve doble",
    "X":"equis","Y":"i griega","Z":"zeta"
}

# ============================================================
# Словники назв літер (кирилиця)
# ============================================================
LETTER_NAMES_CYR_UK = {
    "А":"а","Б":"бе","В":"ве","Г":"ге","Ґ":"ґе","Д":"де","Е":"е","Є":"є","Ж":"же","З":"зе",
    "И":"и","І":"і","Ї":"ї","Й":"й","К":"ка","Л":"ел","М":"ем","Н":"ен","О":"о","П":"пе",
    "Р":"ер","С":"ес","Т":"те","У":"у","Ф":"еф","Х":"ха","Ц":"це","Ч":"че","Ш":"ша","Щ":"ща",
    "Ь":"м'який знак","Ю":"ю","Я":"я"
}
LETTER_NAMES_CYR_RU = {
    "А":"а","Б":"бэ","В":"вэ","Г":"гэ","Д":"дэ","Е":"е","Ё":"ё","Ж":"же","З":"зэ","И":"и",
    "Й":"й","К":"ка","Л":"эл","М":"эм","Н":"эн","О":"о","П":"пэ","Р":"эр","С":"эс","Т":"тэ",
    "У":"у","Ф":"эф","Х":"ха","Ц":"цэ","Ч":"че","Ш":"ша","Щ":"ща","Ъ":"твёрдый знак","Ы":"ы",
    "Ь":"мягкий знак","Э":"э","Ю":"ю","Я":"я"
}

# ============================================================
# Мапа словників за мовами
# ============================================================
LETTER_DICTS_LAT = {
    "en": LETTER_NAMES_US,
    "fr": LETTER_NAMES_FR,
    "de": LETTER_NAMES_DE,
    "es": LETTER_NAMES_ES,
}
LETTER_DICTS_CYR = {
    "uk": LETTER_NAMES_CYR_UK,
    "ru": LETTER_NAMES_CYR_RU,
}

# ============================================================
# Виключення та кастомні заміни
# ============================================================
ABBREV_EXCEPTIONS = {
    "NASA","NATO","UNESCO","UNICEF","OPEC","LASER","RADAR","SCUBA","FIFA","OECD",
    "ДТЕК","ЮНІСЕФ","НАТО","САП","ГУР","SECRET","BOX","KAIRO","VIRAT","ЦЕНЗУРИ"
}
CUSTOM_ABBREV_MAP = {
    "ДСНС": "Державна служба з надзвичайних ситуацій",
    "СБУ": "Служба Безпеки України",
    "ДСНС": "Державна служба з надзвичайних ситуацій"
}

# ============================================================
# Мапа голосів для TTS
# ============================================================
VOICE_MAP = {
    "en": ("en","v3_en","en"),
    "uk": ("ua","v3_ua","uk"),
    "ru": ("ru","v5_ru","ru"),
    "fr": ("fr","v3_fr","fr"),
    "de": ("de","v3_de","de"),
    "es": ("es","v3_es","es"),
}

loaded_models = {}

# ============================================================
# 1. Визначення домінантної мови
# ============================================================
def detect_dominant_language(text):
    try:
        lang = detect(text)
        return lang if lang in VOICE_MAP else "uk"
    except Exception:
        return "uk"

# ============================================================
# 2. Розбиття на мовні фрагменти
# ============================================================
def split_by_sentences(text):
    return re.split(r'(?<=[.!?])\s+', text)

def split_mixed_sentence(sentence, dominant_lang):
    # Розбиваємо на токени
    token_pattern = r'([а-яА-ЯіїєґІЇЄҐёЁыЫъЭ]+|[A-Za-z]+|\d+|[^\w\s]+|\s+)'
    tokens = re.findall(token_pattern, sentence)

    result = []

    for token in tokens:
        if not token.strip():
            if result:
                result[-1] = (result[-1][0], result[-1][1] + token)
            continue

        # Визначаємо тип токена
        is_cyr = bool(re.search(r"[а-яА-ЯіїєґІЇЄҐёЁыЫъЭ]", token))
        is_lat = bool(re.search(r"[A-Za-z]", token))
        is_punct = bool(re.match(r"^[^\w\s]+$", token))
        is_digit = bool(re.match(r"^\d+$", token))

        if is_punct or is_digit:
            lang = dominant_lang
        elif is_cyr:
            if re.search(r"[іїєґІЇЄҐ]", token):
                lang = "uk"
            elif re.search(r"[ёЁыЫъЭ]", token):
                lang = "ru"
            elif dominant_lang in ["uk", "ru"]:
                lang = dominant_lang
            else:
                lang = "uk"
        elif is_lat:
            try:
                if len(token) <= 10 or token.isupper():
                    lang = "en"
                else:
                    detected = detect(token)
                    lang = detected if detected in VOICE_MAP else "en"
            except Exception:
                lang = "en"
        else:
            lang = dominant_lang

        result.append((lang, token))

    return result

def merge_adjacent_tokens(tokens):
    if not tokens:
        return []

    merged = []
    current_lang, current_text = tokens[0]

    for lang, text in tokens[1:]:
        if lang == current_lang:
            current_text += text
        else:
            if current_text.strip():
                merged.append((current_lang, current_text))
            current_lang = lang
            current_text = text

    if current_text.strip():
        merged.append((current_lang, current_text))

    return merged

def process_sentence_mixed(sentence, dominant_lang):
    tokens = split_mixed_sentence(sentence, dominant_lang)
    merged = merge_adjacent_tokens(tokens)
    return merged

def group_sentences_by_language(text):
    dominant_lang = detect_dominant_language(text)
    sentences = split_by_sentences(text)

    all_fragments = []

    for sentence in sentences:
        if not sentence.strip():
            continue

        sent_fragments = process_sentence_mixed(sentence, dominant_lang)
        all_fragments.extend(sent_fragments)

    # Очищаємо від порожніх фрагментів
    cleaned = []
    for lang, text in all_fragments:
        if re.search(r'[а-яА-ЯіїєґІЇЄҐёЁыЫъЭA-Za-z]', text):
            cleaned.append((lang, text))

    return dominant_lang, cleaned

# ============================================================
# 3. Нормалізація
# ============================================================
ABBREV_PATTERN = re.compile(r"\b(?:[A-Z]{2,}|[А-ЯІЇЄҐЁЫЭ]{2,})\b")

def normalize_abbreviations(text, lang_code):
    def repl(match):
        token = match.group(0)

        if token in CUSTOM_ABBREV_MAP:
            return CUSTOM_ABBREV_MAP[token]

        if token in ABBREV_EXCEPTIONS:
            return token

        if token.isupper():
            is_cyr = bool(re.search(r"[А-ЯІЇЄҐЁЫЭ]", token))
            dict_for_lang = LETTER_DICTS_CYR.get(lang_code, LETTER_NAMES_CYR_UK) if is_cyr else LETTER_DICTS_LAT.get(lang_code, LETTER_NAMES_US)
            spoken = [dict_for_lang.get(ch, ch) for ch in token]
            return " ".join(spoken)

        return token

    return ABBREV_PATTERN.sub(repl, text)

def normalize_numbers(text, num_lang):
    text = re.sub(
        r"\b24/7\b",
        f"{num2words(24, lang=num_lang)} на {num2words(7, lang=num_lang)}",
        text
    )

    def replacer(match):
        num_str = match.group()

        if "." in num_str or "," in num_str:
            parts = re.split(r"[.,]", num_str)
            try:
                whole = num2words(int(parts[0]), lang=num_lang)
                frac = " ".join([num2words(int(d), lang=num_lang) for d in parts[1]])
                return f"{whole} кома {frac}" if num_lang == "uk" else f"{whole} point {frac}"
            except Exception:
                return num_str
        elif "%" in num_str:
            try:
                num = int(num_str.replace("%", ""))
                words = num2words(num, lang=num_lang)
                return f"{words} відсотків" if num_lang == "uk" else f"{words} percent"
            except Exception:
                return num_str
        else:
            try:
                return num2words(int(num_str), lang=num_lang)
            except Exception:
                return " ".join(list(num_str))

    return re.sub(r"\d+[.,]?\d*%?", replacer, text)

def normalize_dates(text, date_lang):
    def replacer(match):
        date_str = match.group()
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                date = datetime.datetime.strptime(date_str, fmt).date()
                if date_lang == "uk":
                    months_ua = ["січня","лютого","березня","квітня","травня","червня",
                               "липня","серпня","вересня","жовтня","листопада","грудня"]
                    return f"{date.day} {months_ua[date.month-1]} {date.year} року"
                elif date_lang == "ru":
                    return date.strftime("%d %B %Y года")
                else:
                    return date.strftime("%B %d, %Y")
            except ValueError:
                continue
        return date_str

    return re.sub(r"\d{4}-\d{2}-\d{2}|\d{2}[./]\d{2}[./]\d{4}", replacer, text)

# ============================================================
# 4. Розбиття на чанки
# ============================================================
def split_into_chunks(text, max_len=1000):
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

# ============================================================
# 5. TTS
# ============================================================
def load_model(language, default_speaker):
    if language in loaded_models:
        return loaded_models[language]

    try:
        model, _ = torch.hub.load(
            repo_or_dir='snakers4/silero-models',
            model='silero_tts',
            language=language,
            speaker=default_speaker
        )
        loaded_models[language] = model
        return model
    except Exception as e:
        print(f"Помилка завантаження моделі для {language}: {e}")
        return None

def synthesize_fragment(lang_code, text):
    if lang_code not in VOICE_MAP:
        return None

    language, default_speaker, num_lang = VOICE_MAP[lang_code]

    # Нормалізація
    text = normalize_abbreviations(text, lang_code)

    if re.search(r"\d", text):
        text = normalize_numbers(text, num_lang)

    if re.search(r"\d{4}-\d{2}-\d{2}|\d{2}[./]\d{2}[./]\d{4}", text):
        text = normalize_dates(text, num_lang)

    # Розбиття на чанки
    chunks = split_into_chunks(text, max_len=1000)

    # Завантаження моделі
    model = load_model(language, default_speaker)
    if model is None:
        return None

    speaker = default_speaker if default_speaker in getattr(model, 'speakers', []) else model.speakers[0]

    # Озвучення
    audio_parts = []
    for chunk in chunks:
        try:
            audio = model.apply_tts(text=chunk, speaker=speaker, sample_rate=48000)
            audio_parts.append(audio)
        except Exception as e:
            print(f"Помилка синтезу чанка: {e}")
            continue

    if not audio_parts:
        return None

    return np.concatenate(audio_parts)

# ============================================================
# UI
# ============================================================
def show_message(title, text, is_error=False):
    root = tk.Tk()
    root.withdraw()
    if is_error:
        messagebox.showerror(title, text)
    else:
        messagebox.showinfo(title, text)
    root.destroy()

# ============================================================
# MAIN
# ============================================================
def main():
    text = pyperclip.paste().strip()
    if not text:
        show_message("Помилка", "Буфер порожній", is_error=True)
        return

    #print("="*80)
    #print("Оригінальний текст:")
    #print(text[:500] + ("..." if len(text) > 500 else ""))
    #print("="*80)

    # Визначення та розбиття
    dominant_lang, fragments = group_sentences_by_language(text)
    #print(f"\nДомінантна мова: {dominant_lang}")
    #print(f"Знайдено {len(fragments)} мовних фрагментів")

    for idx, (lang, frag) in enumerate(fragments, 1):
        preview = frag[:100].replace("\n", " ")
        #print(f"  {idx}. [{lang}] {preview}{'...' if len(frag) > 100 else ''}")

    if not fragments:
        show_message("Помилка", "Не вдалося визначити мову", is_error=True)
        return

    # Озвучення
    #print(f"\nСинтез аудіо:")
    all_audio_segments = []

    for idx, (lang, frag) in enumerate(fragments, 1):
        #print(f"\n  Фрагмент {idx}/{len(fragments)} [{lang}]")
        audio = synthesize_fragment(lang, frag)

        if audio is not None:
            all_audio_segments.append(audio)
            #print(f"    Озвучено ({len(audio)} samples, {len(audio)/48000:.1f}s)")
        else:
            print(f"    Не вдалося озвучити")

    if not all_audio_segments:
        show_message("Помилка", "Не вдалося створити аудіо", is_error=True)
        return

    # Склеювання
    full_audio = np.concatenate(all_audio_segments)

    buffer = BytesIO()
    sf.write(buffer, full_audio, 48000, format="WAV")
    buffer.seek(0)

    # Визначення шляху
    xdg_download = os.path.expanduser("~/Downloads")
    config_file = os.path.expanduser("~/.config/user-dirs.dirs")

    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                for line in f:
                    if line.startswith("XDG_DOWNLOAD_DIR"):
                        path = line.split("=")[1].strip().strip('"')
                        xdg_download = os.path.expandvars(path)
        except Exception:
            pass

    output_file = os.path.join(xdg_download, "111.mp3")

    # Конвертація в MP3
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", "pipe:0", "-f", "mp3", output_file],
        input=buffer.read(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if proc.returncode == 0:
        #print(f"\nЗбережено у {output_file}")
        print(f"Загальна тривалість: {len(full_audio)/48000:.1f} секунд")

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
