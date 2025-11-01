import base64
import cv2
import pyshine as ps
import xml.etree.ElementTree as ET

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

from skimage.metrics import structural_similarity as ssim
import numpy as np

from logging_controller import get_logger

from config import load_config
configs = load_config()

try:
    logger = get_logger()
except Exception as e:
    print(f"ERROR: Failed to load logger configuration: {e}")
    sys.exit(1)

class AndroidElement:
    def __init__(self, uid, bbox, attrib):
        self.uid = uid
        self.bbox = bbox
        self.attrib = attrib

def area_to_xy(area, subarea, height, width, rows, cols):
    area -= 1
    row, col = area // cols, area % cols
    x_0, y_0 = col * (width // cols), row * (height // rows)
    if subarea == "top-left":
        x, y = x_0 + (width // cols) // 4, y_0 + (height // rows) // 4
    elif subarea == "top":
        x, y = x_0 + (width // cols) // 2, y_0 + (height // rows) // 4
    elif subarea == "top-right":
        x, y = x_0 + (width // cols) * 3 // 4, y_0 + (height // rows) // 4
    elif subarea == "left":
        x, y = x_0 + (width // cols) // 4, y_0 + (height // rows) // 2
    elif subarea == "right":
        x, y = x_0 + (width // cols) * 3 // 4, y_0 + (height // rows) // 2
    elif subarea == "bottom-left":
        x, y = x_0 + (width // cols) // 4, y_0 + (height // rows) * 3 // 4
    elif subarea == "bottom":
        x, y = x_0 + (width // cols) // 2, y_0 + (height // rows) * 3 // 4
    elif subarea == "bottom-right":
        x, y = x_0 + (width // cols) * 3 // 4, y_0 + (height // rows) * 3 // 4
    else:
        x, y = x_0 + (width // cols) // 2, y_0 + (height // rows) // 2
    return x, y

def draw_grid(img_path, output_path, rows=None, cols=None, min_cell_px=40):
    """
    Draw a grid on the image.
    - If rows/cols are provided, they are used directly.
    - Otherwise, grid density is derived from min_cell_px (smaller => more cells).
    """
    try:
        def clamp(n, lo, hi):
            return max(lo, min(hi, n))

        min_cell_px = configs.get("GRID_SIZE", 40)

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
    except Exception as e:
        logger.error(f"ERROR in draw_grid: {e}")
        return 0, 0

def encode_image(image_path, max_width=800, quality=75):
    try:
        with Image.open(image_path) as img:
            # Resize proportionally if width is larger than max_width
            if img.width > max_width:
                ratio = max_width / float(img.width)
                new_height = int(float(img.height) * ratio)
                try:
                    resample = Image.Resampling.LANCZOS
                except AttributeError:
                    # Fallback for older Pillow versions
                    resample = Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS
                img = img.resize((max_width, new_height), resample)
                # img = img.resize((max_width, new_height), Image.ANTIALIAS)
            # Save to bytes buffer with lower quality
            # Convert to RGB if necessary (some PNGs have RGBA which JPEG doesn't support)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create a white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=quality)
            # Encode base64 string
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return img_str
    except Exception as e:
        logger.error(f"ERROR in encode_image: {e}")
        return ""

def calculate_image_similarity(img_path1, img_path2):
    def load_image_as_gray(image_path, max_width=800):
        if not image_path:
            return None
        try:
            with Image.open(image_path) as img:
                if img.width > max_width:
                    ratio = max_width / float(img.width)
                    new_height = int(float(img.height) * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                img_gray = img.convert("L")
                return np.array(img_gray)
        except Exception as e:
            logger.error(f"ERROR loading image {image_path}: {e}")
            return None

    try:
        img1 = load_image_as_gray(img_path1)
        img2 = load_image_as_gray(img_path2)

        # Handle empty or missing images
        if img1 is None and img2 is None:
            return 1.0  # Both missing, consider identical
        if img1 is None or img2 is None:
            return 0.0  # One missing, dissimilar

        # Resize for dimension compatibility
        min_height = min(img1.shape[0], img2.shape[0])
        min_width = min(img1.shape[1], img2.shape[1])
        _resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.BICUBIC)
        img1_resized = Image.fromarray(img1).resize((min_width, min_height), _resample)
        img2_resized = Image.fromarray(img2).resize((min_width, min_height), _resample)

        img1_array = np.array(img1_resized)
        img2_array = np.array(img2_resized)

        score, _ = ssim(img1_array, img2_array, full=True)
        return score
    except Exception as e:
        logger.error(f"ERROR computing similarity: {e}")
        return 0.0

def get_id_from_element(elem):
    bounds = elem.attrib["bounds"][1:-1].split("][")
    x1, y1 = map(int, bounds[0].split(","))
    x2, y2 = map(int, bounds[1].split(","))
    elem_w, elem_h = x2 - x1, y2 - y1
    if "resource-id" in elem.attrib and elem.attrib["resource-id"]:
        elem_id = elem.attrib["resource-id"].replace(":", ".").replace("/", "_")
    else:
        elem_id = f"{elem.attrib['class']}_{elem_w}_{elem_h}"
    if "content-desc" in elem.attrib and elem.attrib["content-desc"] and len(elem.attrib["content-desc"]) < 20:
        content_desc = elem.attrib['content-desc'].replace("/", "_").replace(" ", "").replace(":", "_")
        elem_id += f"_{content_desc}"
    return elem_id

def traverse_tree(xml_path, elem_list, attrib, add_index=False):
    path = []
    for event, elem in ET.iterparse(xml_path, ['start', 'end']):
        if event == 'start':
            path.append(elem)
            if attrib in elem.attrib and elem.attrib[attrib] == "true":
                parent_prefix = ""
                if len(path) > 1:
                    parent_prefix = get_id_from_element(path[-2])
                bounds = elem.attrib["bounds"][1:-1].split("][")
                x1, y1 = map(int, bounds[0].split(","))
                x2, y2 = map(int, bounds[1].split(","))
                center = (x1 + x2) // 2, (y1 + y2) // 2
                elem_id = get_id_from_element(elem)
                if parent_prefix:
                    elem_id = parent_prefix + "_" + elem_id
                if add_index:
                    elem_id += f"_{elem.attrib['index']}"
                close = False
                for e in elem_list:
                    bbox = e.bbox
                    center_ = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2
                    dist = (abs(center[0] - center_[0]) ** 2 + abs(center[1] - center_[1]) ** 2) ** 0.5
                    if dist <= configs["MIN_DIST"]:
                        close = True
                        break
                if not close:
                    elem_list.append(AndroidElement(elem_id, ((x1, y1), (x2, y2)), attrib))

        if event == 'end':
            path.pop()

def collect_interactive_elements(xml_path, min_area=2000, iou_thresh=0.6):
    elems = []
    path = []
    # Gather all nodes first so we can apply heuristics after traversal
    for event, elem in ET.iterparse(xml_path, ['start', 'end']):
        if event == 'start':
            path.append(elem)
            try:
                bounds = elem.attrib.get("bounds")
                if not bounds:
                    continue
                b = bounds[1:-1].split("][")
                x1, y1 = map(int, b[0].split(","))
                x2, y2 = map(int, b[1].split(","))
                w, h = x2 - x1, y2 - y1
                area = w * h
                if area < min_area:
                    continue

                # Heuristics for “interactive”
                clickable = elem.attrib.get("clickable") == "true"
                focusable = elem.attrib.get("focusable") == "true"
                long_clickable = elem.attrib.get("long-clickable") == "true"
                scrollable = elem.attrib.get("scrollable") == "true"
                has_id = bool(elem.attrib.get("resource-id"))
                has_desc = bool(elem.attrib.get("content-desc"))

                is_interactive = clickable or focusable or long_clickable or scrollable or has_id or has_desc
                if not is_interactive:
                    continue

                # Prefer labeling by parent context when available
                parent_prefix = ""
                if len(path) > 1:
                    parent_prefix = get_id_from_element(path[-2])

                elem_id = get_id_from_element(elem)
                if parent_prefix:
                    elem_id = parent_prefix + "_" + elem_id

                # attribute tag for coloring in draw
                attrib_tag = "clickable" if clickable else ("focusable" if focusable else ("scrollable" if scrollable else "long_clickable"))

                elems.append(AndroidElement(elem_id, ((x1, y1), (x2, y2)), attrib_tag))
            except Exception:
                pass

        elif event == 'end':
            path.pop()

    # De-duplicate by IoU to keep distinct tiles
    def iou(a, b):
        (ax1, ay1), (ax2, ay2) = a
        (bx1, by1), (bx2, by2) = b
        xL, yT = max(ax1, bx1), max(ay1, by1)
        xR, yB = min(ax2, bx2), min(ay2, by2)
        if xR <= xL or yB <= yT:
            return 0.0
        inter = (xR - xL) * (yB - yT)
        areaA = (ax2 - ax1) * (ay2 - ay1)
        areaB = (bx2 - bx1) * (by2 - by1)
        return inter / max(areaA + areaB - inter, 1e-6)

    merged = []
    for e in elems:
        keep = True
        for m in merged:
            if iou(m.bbox, e.bbox) > iou_thresh:
                keep = False
                break
        if keep:
            merged.append(e)
    return merged

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
            logger.error(f"ERROR: An exception occurs while labeling the image\n{e}")
        count += 1
    cv2.imwrite(output_path, imgcv)
    return imgcv

def speak(text: str):
    # macOS native TTS; configurable
    try:
        if sys.platform == "darwin":
            voice = configs.get("VOICE_TYPE", "Veena")
            rate = configs.get("VOICE_SPEED", 170)
            cmd = ["say"]
            if voice:
                cmd += ["-v", voice]
            if rate:
                cmd += ["-r", rate]
            cmd += [text]
            subprocess.run(cmd, check=False)
    except Exception:
        pass

def _record_wav_tmp(seconds=12, samplerate=16000, channels=1):
    try:
        # Record audio from default input into a temp wav file and return its path
        audio = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=channels, dtype="int16")
        sd.wait()
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        sf.write(path, audio, samplerate)
        return path
    except Exception as e:
        logger.error(f"Error during audio recording: {e}")
        return None

def transcribe_with_openai(wav_path: str):
    try:
        url = configs.get("OPENAI_API_WHISPER_URL", "https://api.openai.com/v1/audio/transcriptions")
        model = configs.get("OPENAI_WHISPER_MODEL", "whisper-1")
        api_key = configs.get("OPENAI_API_KEY", "")
        headers = {"Authorization": f"Bearer {api_key}"}
        with open(wav_path, "rb") as f:
            files = {
                "file": (os.path.basename(wav_path), f, "audio/wav"),
                "model": (None, model),
                "language": (None, "en"), # Force decoding for English
                "translate": (None, "true"), # Translate non-English speech into English
                "temperature": (None, "0"), # More deterministic
            }
            resp = requests.post(url, headers=headers, files=files, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data.get("text", "").strip()
    except OSError as oe:
        logger.error(f"File error: {oe}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

def voice_ask(prompt_text: str, max_seconds: int = 15) -> str:
    # Speak prompt, record answer, transcribe; fallback to keyboard if empty/failed
    logger.show(prompt_text)
    # logger.show("Activating voice agent")
    speak(prompt_text)
    try:
        wav_path = _record_wav_tmp(seconds=max_seconds)
        try:
            text = transcribe_with_openai(wav_path)
            cost_per_minute = 0.006
            usage_cost = (max_seconds / 60) * cost_per_minute
            # logger.debug(f"Estimated transcription cost: ${usage_cost:.6f}")
            speak(text)
        finally:
            try:
                os.remove(wav_path)
            except Exception:
                pass
        if text:
            logger.show(f"(Voice Response): {text}")
            return text
    except Exception as e:
        logger.error(f"Voice input failed: {e}")
    # Fallback to manual input
    return input()
