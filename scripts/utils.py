import base64
import cv2
import pyshine as ps

from colorama import Fore, Style

from PIL import Image
import io
import base64

import os
import subprocess
import tempfile
import requests
import sys
import sounddevice as sd
import soundfile as sf

# from config import load_config
# configs = load_config()

def print_with_color(text: str, color=""):
    if color == "red":
        print(Fore.RED + text)
    elif color == "green":
        print(Fore.GREEN + text)
    elif color == "yellow":
        print(Fore.YELLOW + text)
    elif color == "blue":
        print(Fore.BLUE + text)
    elif color == "magenta":
        print(Fore.MAGENTA + text)
    elif color == "cyan":
        print(Fore.CYAN + text)
    elif color == "white":
        print(Fore.WHITE + text)
    elif color == "black":
        print(Fore.BLACK + text)
    else:
        print(text)
    print(Style.RESET_ALL)


def draw_bbox_multi(img_path, output_path, elem_list, record_mode=False, dark_mode=False):
    imgcv = cv2.imread(img_path)
    count = 1
    for elem in elem_list:
        try:
            top_left = elem.bbox[0]
            bottom_right = elem.bbox[1]
            left, top = top_left[0], top_left[1]
            right, bottom = bottom_right[0], bottom_right[1]
            label = str(count)
            if record_mode:
                if elem.attrib == "clickable":
                    color = (250, 0, 0)
                elif elem.attrib == "focusable":
                    color = (0, 0, 250)
                else:
                    color = (0, 250, 0)
                imgcv = ps.putBText(imgcv, label, text_offset_x=(left + right) // 2 + 10, text_offset_y=(top + bottom) // 2 + 10,
                                    vspace=10, hspace=10, font_scale=1, thickness=2, background_RGB=color,
                                    text_RGB=(255, 250, 250), alpha=0.5)
            else:
                text_color = (10, 10, 10) if dark_mode else (255, 250, 250)
                bg_color = (255, 250, 250) if dark_mode else (10, 10, 10)
                imgcv = ps.putBText(imgcv, label, text_offset_x=(left + right) // 2 + 10, text_offset_y=(top + bottom) // 2 + 10,
                                    vspace=10, hspace=10, font_scale=1, thickness=2, background_RGB=bg_color,
                                    text_RGB=text_color, alpha=0.5)
        except Exception as e:
            print_with_color(f"ERROR: An exception occurs while labeling the image\n{e}", "red")
        count += 1
    cv2.imwrite(output_path, imgcv)
    return imgcv


def draw_grid(img_path, output_path, rows=None, cols=None, min_cell_px=40):
    """
    Draw a grid on the image.
    - If rows/cols are provided, they are used directly.
    - Otherwise, grid density is derived from min_cell_px (smaller => more cells).
    """
    def clamp(n, lo, hi):
        return max(lo, min(hi, n))

    image = cv2.imread(img_path)
    height, width, _ = image.shape
    color = (255, 116, 113)

    if rows is None or cols is None:
        # Derive rows/cols from desired minimum cell size
        rows = clamp(height // min_cell_px, 1, 100)
        cols = clamp(width // min_cell_px, 1, 100)

    # Compute actual cell size from rows/cols
    unit_height = max(1, height // rows)
    unit_width = max(1, width // cols)
    thick = max(1, int(max(unit_width, unit_height) // 50))

    for i in range(rows):
        for j in range(cols):
            label = i * cols + j + 1
            left = int(j * unit_width)
            top = int(i * unit_height)
            right = int((j + 1) * unit_width)
            bottom = int((i + 1) * unit_height)
            cv2.rectangle(image, (left, top), (right, bottom), color, thick // 2)
            cv2.putText(image, str(label),
                        (left + int(unit_width * 0.05), top + int(unit_height * 0.3)),
                        0, max(0.5, 0.01 * unit_width), color, thick)
    cv2.imwrite(output_path, image)
    return rows, cols

def encode_image(image_path, max_width=800, quality=75):
    with Image.open(image_path) as img:
        # Resize proportionally if width is larger than max_width
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(float(img.height) * ratio)
            img = img.resize((max_width, new_height), Image.ANTIALIAS)
        # Save to bytes buffer with lower quality
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=quality)
        # Encode base64 string
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str


def speak(text: str):
    # macOS native TTS; no-op fallback on other OSes
    try:
        if sys.platform == "darwin":
            subprocess.run(["say", text], check=False)
    except Exception:
        pass

def _record_wav_tmp(seconds=12, samplerate=16000, channels=1):
    # Record audio from default input into a temp wav file and return its path
    audio = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=channels, dtype="int16")
    sd.wait()
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    sf.write(path, audio, samplerate)
    return path

def transcribe_with_openai(wav_path: str, api_key: str, model: str = "whisper-1"):
    # url = configs.get("OPENAI_API_WHISPER_URL", "https://api.openai.com/v1/audio/transcriptions")
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    with open(wav_path, "rb") as f:
        files = {
            "file": (os.path.basename(wav_path), f, "audio/wav"),
            "model": (None, model),
        }
        resp = requests.post(url, headers=headers, files=files, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data.get("text", "").strip()

def voice_ask(prompt_text: str, api_key: str, model: str = "whisper-1", max_seconds: int = 15) -> str:
    # Speak prompt, record answer, transcribe; fallback to keyboard if empty/failed
    print_with_color(prompt_text, "blue")
    speak(prompt_text)
    try:
        wav_path = _record_wav_tmp(seconds=max_seconds)
        try:
            text = transcribe_with_openai(wav_path, api_key=api_key, model=model)
            cost_per_minute = 0.006
            usage_cost = (max_seconds / 60) * cost_per_minute
            print_with_color(f"Estimated transcription cost: ${usage_cost:.6f}", "yellow")
            speak(text)
        finally:
            try:
                os.remove(wav_path)
            except Exception:
                pass
        if text:
            print_with_color(f"(Heard) {text}", "cyan")
            return text
    except Exception as e:
        print_with_color(f"Voice input failed: {e}", "red")
    # Fallback to manual input
    return input()
