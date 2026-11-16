import os
import sys
import io
import json
import uuid
import time
import math
import re
import threading
import subprocess
import shutil
import queue
import secrets
import urllib.request
import argparse
import webbrowser
from functools import wraps
from pathlib import Path

# Ensure UTF-8 output on Windows terminal
if sys.platform.startswith("win") and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Prevent console/CMD window popup when running ffmpeg/subprocesses on Windows
SUBPROCESS_FLAGS = 0
STARTUPINFO = None
SUBPROCESS_KWARGS = {}
if sys.platform == "win32":
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    STARTUPINFO.wShowWindow = 0
    SUBPROCESS_KWARGS = {
        "creationflags": SUBPROCESS_FLAGS,
        "startupinfo": STARTUPINFO
    }

from flask import Flask, request, jsonify, render_template, send_file, Response, send_from_directory
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

# Directory and environment detection
IS_FROZEN = getattr(sys, "frozen", False)
if IS_FROZEN:
    EXE_DIR = Path(sys.executable).parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", EXE_DIR))
    BASE_DIR = EXE_DIR
    STATIC_DIR = BUNDLE_DIR / "static"
    TEMPLATE_DIR = BUNDLE_DIR / "templates"
else:
    BASE_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = BASE_DIR
    STATIC_DIR = BASE_DIR / "static"
    TEMPLATE_DIR = BASE_DIR / "templates"

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
THUMBNAIL_DIR = UPLOAD_DIR / "thumbnails"
FONT_DIR = STATIC_DIR / "fonts"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
THUMBNAIL_DIR.mkdir(exist_ok=True)
FONT_DIR.mkdir(exist_ok=True)

# Resolve FFmpeg binary
def resolve_ffmpeg_exe():
    candidates = [
        BASE_DIR / "ffmpeg.exe",
        BUNDLE_DIR / "ffmpeg.exe",
        BASE_DIR / "ffmpeg",
        BUNDLE_DIR / "ffmpeg",
        Path("/opt/homebrew/bin/ffmpeg"),
        Path("/usr/local/bin/ffmpeg"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

FFMPEG_EXE = resolve_ffmpeg_exe()

def resolve_realesrgan_exe():
    """Locate bundled or local realesrgan-ncnn-vulkan binary and its models directory."""
    exe_names = ["realesrgan-ncnn-vulkan.exe", "realesrgan-ncnn-vulkan"]
    search_dirs = [
        BASE_DIR / "realesrgan",
        BUNDLE_DIR / "realesrgan",
        BASE_DIR,
        BUNDLE_DIR,
    ]
    for d in search_dirs:
        for name in exe_names:
            candidate = d / name
            if candidate.exists():
                models_dir = d / "models"
                return str(candidate), (str(models_dir) if models_dir.exists() else None)
    return None, None

REALESRGAN_EXE, REALESRGAN_MODELS_DIR = resolve_realesrgan_exe()

def pick_realesrgan_model(models_dir):
    """Pick the best available Real-ESRGAN model (prefer fast video model, fallback to x4plus)."""
    if not models_dir:
        return "realesr-animevideov3"
    p = Path(models_dir)
    for name in ("realesr-animevideov3-x4", "realesrgan-x4plus", "realesrgan-x4plus-anime"):
        if (p / f"{name}.param").exists() and (p / f"{name}.bin").exists():
            return name
    return "realesr-animevideov3"

app = Flask(__name__, static_folder=str(STATIC_DIR), template_folder=str(TEMPLATE_DIR))
CORS(app)

# Global task storage for background exports
tasks = {}
SERVER_PORT = 8765
API_CONFIG_PATH = BASE_DIR / "api_config.json"
api_config_lock = threading.Lock()
api_job_queue = queue.Queue()
_api_worker_started = False


def load_api_config():
    """Load or initialize persistent Webhook API configuration."""
    with api_config_lock:
        default_cfg = {
            "api_enabled": True,
            "api_key": f"mvt_{secrets.token_hex(20)}",
            "port": 8765,
            "retention_hours": 0,
        }
        if API_CONFIG_PATH.exists():
            try:
                with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in default_cfg.items():
                    data.setdefault(k, v)
                return data
            except Exception:
                pass
        try:
            with open(API_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(default_cfg, f, indent=2)
        except Exception:
            pass
        return default_cfg


def save_api_config(cfg):
    """Persist Webhook API configuration to disk."""
    with api_config_lock:
        with open(API_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)


def get_output_storage_stats():
    """Return file count and total size in MB inside OUTPUT_DIR."""
    files = [p for p in OUTPUT_DIR.glob("*") if p.is_file()]
    total_bytes = sum(p.stat().st_size for p in files)
    return {
        "file_count": len(files),
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 2),
    }


def require_api_key(fn):
    """Decorator enforcing X-API-Key (or Bearer token) for /api/v1/* endpoints."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        cfg = load_api_config()
        if not cfg.get("api_enabled", True):
            return jsonify({"error": "Webhook API is currently disabled in MergeVideoTool settings"}), 503
        provided = (
            request.headers.get("X-API-Key")
            or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            or request.args.get("api_key", "")
        )
        if not provided or not secrets.compare_digest(provided, cfg.get("api_key", "")):
            return jsonify({"error": "Invalid or missing X-API-Key"}), 401
        return fn(*args, **kwargs)
    return wrapper


def send_webhook_callback(webhook_url, payload):
    """Best-effort POST callback to an external automation webhook (n8n, Make, etc.)."""
    if not webhook_url:
        return
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "MergeVideoTool-Webhook/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15):
            pass
    except Exception:
        pass


def download_remote_video(url, dest_path):
    """Download an HTTP/HTTPS video clip into dest_path for API processing."""
    req = urllib.request.Request(url, headers={"User-Agent": "MergeVideoTool/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest_path, "wb") as out:
        shutil.copyfileobj(resp, out)

def get_font_path(font_name):
    """Resolve font path based on user selection with safe fallbacks across Windows and macOS."""
    font_map = {
        "BeVietnamPro": FONT_DIR / "BeVietnamPro-Bold.ttf",
        "Montserrat": FONT_DIR / "Montserrat.ttf",
        "Arial": Path("C:/Windows/Fonts/arialbd.ttf") if sys.platform == "win32" else Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        "SegoeUI": Path("C:/Windows/Fonts/segoeuib.ttf"),
        "Times": Path("C:/Windows/Fonts/timesbd.ttf") if sys.platform == "win32" else Path("/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"),
        "Calibri": Path("C:/Windows/Fonts/calibrib.ttf"),
    }
    
    selected = font_map.get(font_name)
    if selected and selected.exists():
        return str(selected)
    
    # Fallback search
    for candidate in [
        FONT_DIR / "BeVietnamPro-Bold.ttf",
        FONT_DIR / "Montserrat.ttf",
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/Helvetica.ttc"),
        Path("/Library/Fonts/Arial.ttf"),
    ]:
        if candidate.exists():
            return str(candidate)
            
    return None

def get_video_info(file_path):
    """Probe video metadata using ffmpeg."""
    cmd = [FFMPEG_EXE, "-i", str(file_path)]
    p = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore",
        **SUBPROCESS_KWARGS
    )
    stderr = p.stderr

    duration = 0.0
    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", stderr)
    if dur_match:
        h, m, s = map(float, dur_match.groups())
        duration = round(h * 3600 + m * 60 + s, 2)

    width = 720
    height = 1280
    dim_match = re.search(r"Stream.*Video:.*,\s*(\d{2,5})x(\d{2,5})", stderr)
    if dim_match:
        width = int(dim_match.group(1))
        height = int(dim_match.group(2))

    fps = 30.0
    fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", stderr)
    if fps_match:
        fps = float(fps_match.group(1))

    has_audio = bool(re.search(r"Stream.*Audio:", stderr))

    # Detailed stream properties (used to preserve quality when merging)
    v_codec, a_codec = "", ""
    v_kbps, a_kbps, a_rate = 0, 0, 0
    for line in stderr.splitlines():
        if "Video:" in line and not v_codec:
            m = re.search(r"Video:\s*([\w]+)", line)
            v_codec = m.group(1) if m else ""
            m = re.search(r"(\d+)\s*kb/s", line)
            v_kbps = int(m.group(1)) if m else 0
            m = re.search(r"(\d+(?:\.\d+)?)\s*fps", line)
            if m:
                fps = float(m.group(1))
        elif "Audio:" in line and not a_codec:
            m = re.search(r"Audio:\s*([\w]+)", line)
            a_codec = m.group(1) if m else ""
            m = re.search(r"(\d+)\s*kb/s", line)
            a_kbps = int(m.group(1)) if m else 0
            m = re.search(r"(\d+)\s*Hz", line)
            a_rate = int(m.group(1)) if m else 0

    if v_kbps <= 0:
        # Fall back to container bitrate minus audio
        m = re.search(r"bitrate:\s*(\d+)\s*kb/s", stderr)
        if m:
            v_kbps = max(0, int(m.group(1)) - a_kbps)

    return {
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "has_audio": has_audio,
        "v_codec": v_codec,
        "a_codec": a_codec,
        "v_kbps": v_kbps,
        "a_kbps": a_kbps,
        "a_rate": a_rate,
        "size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else 0
    }

def fps_to_ffmpeg(fps):
    """Convert a probed fps value to an exact ffmpeg frame rate expression."""
    for approx, exact in ((23.98, "24000/1001"), (23.976, "24000/1001"), (29.97, "30000/1001"),
                          (59.94, "60000/1001"), (119.88, "120000/1001")):
        if abs(fps - approx) < 0.006:
            return exact
    return f"{fps:g}"

def can_stream_copy(infos, target_w, target_h):
    """True if all clips share identical encoding so they can be joined without re-encoding."""
    if not infos:
        return False
    f = infos[0]
    if not f["v_codec"]:
        return False
    for i in infos:
        if (i["v_codec"] != f["v_codec"] or i["a_codec"] != f["a_codec"]
                or i["width"] != target_w or i["height"] != target_h
                or abs(i["fps"] - f["fps"]) > 0.01
                or i["a_rate"] != f["a_rate"]
                or i["has_audio"] != f["has_audio"]):
            return False
    return True

def generate_thumbnail(file_path, clip_id):
    """Generate a thumbnail jpeg for a video clip without showing console windows."""
    thumb_path = THUMBNAIL_DIR / f"{clip_id}.jpg"
    if thumb_path.exists():
        return str(thumb_path)

    cmd = [
        FFMPEG_EXE, "-y",
        "-ss", "00:00:01",
        "-i", str(file_path),
        "-vframes", "1",
        "-vf", "scale=360:-1",
        "-q:v", "3",
        str(thumb_path)
    ]
    subprocess.run(cmd, capture_output=True, **SUBPROCESS_KWARGS)
    if not thumb_path.exists():
        # Fallback to 0.1s if video is under 1s
        cmd[3] = "00:00:00.100"
        subprocess.run(cmd, capture_output=True, **SUBPROCESS_KWARGS)

    return str(thumb_path)

def hex_to_rgba(h, alpha=1.0):
    """Convert hex color string to RGBA tuple."""
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    try:
        r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        r, g, b = (255, 255, 255)
    return (r, g, b, max(0, min(255, int(alpha * 255))))

def create_text_badge_image(text, font_family="BeVietnamPro", font_size=40,
                            text_color="#000000", bg_color="#FFFFFF", bg_opacity=1.0,
                            border_radius=14, pad_x=26, pad_y=14, align="center",
                            max_width_px=800, max_height_px=1200, enable_shadow=True):
    """Generate a transparent PNG containing the CapCut-style text badge.
       Maintains user's exact font size, and ONLY auto-adjusts (shrinks) font size when exceeding frame!
    """
    clean_text = text if text and text.strip() else "Nhập nội dung text..."
    font_path = get_font_path(font_family)

    def get_font_obj(sz):
        try:
            if font_path:
                return ImageFont.truetype(font_path, int(sz))
            return ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()

    # Use user's exact chosen font size without auto-shrinking or splitting words
    cur_size = max(10, int(font_size))
    final_font = get_font_obj(cur_size)

    # Lines are strictly based on user's manual line breaks
    lines = clean_text.split("\n")
    if not lines:
        lines = [clean_text]

    line_bboxes = [final_font.getbbox(l) if l else (0, 0, 0, int(cur_size * 0.8)) for l in lines]
    line_heights = [max(int(cur_size * 0.9), (b[3] - b[1])) for b in line_bboxes]
    line_widths = [(b[2] - b[0]) for b in line_bboxes]
    line_spacing = max(4, int(cur_size * 0.25))

    total_text_w = max(line_widths) if line_widths else 40
    total_text_h = sum(line_heights) + line_spacing * max(0, len(lines) - 1)

    box_w = total_text_w + pad_x * 2
    box_h = total_text_h + pad_y * 2

    margin = 12 if enable_shadow else 4
    img_w = box_w + margin * 2
    img_h = box_h + margin * 2

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bg_rgba = hex_to_rgba(bg_color, bg_opacity)
    text_rgba = hex_to_rgba(text_color, 1.0)

    # Draw subtle shadow for premium CapCut sticker look
    if enable_shadow and bg_opacity > 0.05:
        shadow_box = [margin + 1, margin + 4, margin + box_w + 1, margin + box_h + 4]
        draw.rounded_rectangle(shadow_box, radius=border_radius, fill=(0, 0, 0, int(70 * bg_opacity)))

    # Draw main background rounded rectangle
    if bg_opacity > 0.0:
        main_box = [margin, margin, margin + box_w, margin + box_h]
        draw.rounded_rectangle(main_box, radius=border_radius, fill=bg_rgba)

    # Draw text lines
    y_cursor = margin + pad_y
    for i, line in enumerate(lines):
        lw = line_widths[i]
        bbox = line_bboxes[i]
        if align == "center":
            lx = margin + (box_w - lw) // 2
        elif align == "right":
            lx = margin + box_w - pad_x - lw
        else:
            lx = margin + pad_x

        draw.text((lx - bbox[0], y_cursor - bbox[1]), line, font=final_font, fill=text_rgba)
        y_cursor += line_heights[i] + line_spacing

    return img, img_w, img_h

# Web Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/select-files", methods=["POST"])
def select_files():
    """Trigger native Windows File Dialog and return the list of selected paths immediately without blocking for thumbnails."""
    selected_files = []
    
    def run_dialog():
        nonlocal selected_files
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            files = filedialog.askopenfilenames(
                title="Chọn một hoặc nhiều video để ghép",
                filetypes=[
                    ("Video Files", "*.mp4 *.mov *.avi *.mkv *.webm *.flv *.m4v *.wmv"),
                    ("Tất cả tập tin", "*.*")
                ]
            )
            root.destroy()
            selected_files = list(files)
        except Exception as e:
            print("Dialog error:", e)

    t = threading.Thread(target=run_dialog)
    t.start()
    t.join(timeout=120)
    return jsonify({"success": True, "files": selected_files})

@app.route("/api/import-file-path", methods=["POST"])
def import_file_path():
    """Process a single local video file silently: probe metadata, generate thumbnail, return clip."""
    data = request.json or {}
    fp = data.get("path")
    if not fp:
        return jsonify({"error": "Không có đường dẫn tệp"}), 400
    
    fp_path = Path(fp)
    if not fp_path.exists():
        return jsonify({"error": "Tệp không tồn tại"}), 404

    clip_id = str(uuid.uuid4())[:8]
    info = get_video_info(fp_path)
    generate_thumbnail(fp_path, clip_id)

    return jsonify({
        "success": True,
        "clip": {
            "id": clip_id,
            "name": fp_path.name,
            "path": str(fp_path),
            "duration": info["duration"],
            "width": info["width"],
            "height": info["height"],
            "fps": info["fps"],
            "has_audio": info["has_audio"],
            "size_bytes": info["size_bytes"],
            "thumbnail_url": f"/api/thumbnail/{clip_id}"
        }
    })

@app.route("/api/upload-single", methods=["POST"])
def upload_single():
    """Upload and process a single video file silently."""
    if "file" not in request.files:
        return jsonify({"error": "Không có tệp nào"}), 400
    
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Tên tệp không hợp lệ"}), 400

    clip_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename).suffix or ".mp4"
    save_path = UPLOAD_DIR / f"{clip_id}{ext}"
    file.save(str(save_path))

    info = get_video_info(save_path)
    generate_thumbnail(save_path, clip_id)

    return jsonify({
        "success": True,
        "clip": {
            "id": clip_id,
            "name": file.filename,
            "path": str(save_path),
            "duration": info["duration"],
            "width": info["width"],
            "height": info["height"],
            "fps": info["fps"],
            "has_audio": info["has_audio"],
            "size_bytes": info["size_bytes"],
            "thumbnail_url": f"/api/thumbnail/{clip_id}"
        }
    })

@app.route("/api/browse-files", methods=["POST"])
def browse_files():
    """Trigger native Windows File Dialog to let user pick videos directly without slow uploads."""
    selected_files = []
    
    def run_dialog():
        nonlocal selected_files
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            files = filedialog.askopenfilenames(
                title="Chọn một hoặc nhiều video để ghép",
                filetypes=[
                    ("Video Files", "*.mp4 *.mov *.avi *.mkv *.webm *.flv *.m4v *.wmv"),
                    ("Tất cả tập tin", "*.*")
                ]
            )
            root.destroy()
            selected_files = list(files)
        except Exception as e:
            print("Dialog error:", e)

    t = threading.Thread(target=run_dialog)
    t.start()
    t.join(timeout=60)

    results = []
    for fp in selected_files:
        fp_path = Path(fp)
        if not fp_path.exists():
            continue
        clip_id = str(uuid.uuid4())[:8]
        info = get_video_info(fp_path)
        generate_thumbnail(fp_path, clip_id)

        results.append({
            "id": clip_id,
            "name": fp_path.name,
            "path": str(fp_path),
            "duration": info["duration"],
            "width": info["width"],
            "height": info["height"],
            "fps": info["fps"],
            "has_audio": info["has_audio"],
            "size_bytes": info["size_bytes"],
            "thumbnail_url": f"/api/thumbnail/{clip_id}"
        })

    return jsonify({"success": True, "clips": results})

@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Upload video files dropped or selected via browser input."""
    if "files" not in request.files:
        return jsonify({"error": "Không có tệp nào được tải lên"}), 400

    uploaded = request.files.getlist("files")
    results = []

    for file in uploaded:
        if not file.filename:
            continue
        clip_id = str(uuid.uuid4())[:8]
        ext = Path(file.filename).suffix or ".mp4"
        save_path = UPLOAD_DIR / f"{clip_id}{ext}"
        file.save(str(save_path))

        info = get_video_info(save_path)
        generate_thumbnail(save_path, clip_id)

        results.append({
            "id": clip_id,
            "name": file.filename,
            "path": str(save_path),
            "duration": info["duration"],
            "width": info["width"],
            "height": info["height"],
            "fps": info["fps"],
            "has_audio": info["has_audio"],
            "size_bytes": info["size_bytes"],
            "thumbnail_url": f"/api/thumbnail/{clip_id}"
        })

    return jsonify({"success": True, "clips": results})

@app.route("/api/thumbnail/<clip_id>")
def get_thumbnail(clip_id):
    thumb_path = THUMBNAIL_DIR / f"{clip_id}.jpg"
    if thumb_path.exists():
        return send_file(thumb_path, mimetype="image/jpeg")
    return Response(status=404)

@app.route("/api/video-stream")
def stream_video():
    """Stream local video with range request support for smooth browser preview seeking."""
    path = request.args.get("path")
    if not path or not os.path.exists(path):
        return Response("File not found", status=404)

    file_size = os.path.getsize(path)
    range_header = request.headers.get("Range", None)

    if not range_header:
        return send_file(path, mimetype="video/mp4")

    # Parse byte range
    byte_range = range_header.replace("bytes=", "").split("-")
    start = int(byte_range[0])
    end = int(byte_range[1]) if byte_range[1] else file_size - 1
    length = end - start + 1

    with open(path, "rb") as f:
        f.seek(start)
        data = f.read(length)

    response = Response(data, 206, mimetype="video/mp4", direct_passthrough=True)
    response.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
    response.headers.add("Accept-Ranges", "bytes")
    response.headers.add("Content-Length", str(length))
    return response

@app.route("/api/render-preview-badge", methods=["POST"])
def render_preview_badge():
    """Render and return badge PNG for real-time preview check."""
    data = request.json or {}
    text = data.get("text", "CapCut Text")
    font_family = data.get("font_family", "BeVietnamPro")
    font_size = int(data.get("font_size", 42))
    text_color = data.get("text_color", "#000000")
    bg_color = data.get("bg_color", "#FFFFFF")
    bg_opacity = float(data.get("bg_opacity", 1.0))
    border_radius = int(data.get("border_radius", 14))
    pad_x = int(data.get("pad_x", 26))
    pad_y = int(data.get("pad_y", 14))
    align = data.get("align", "center")
    max_w = int(data.get("max_width", 800))
    shadow = bool(data.get("shadow", True))

    img, w, h = create_text_badge_image(
        text=text,
        font_family=font_family,
        font_size=font_size,
        text_color=text_color,
        bg_color=bg_color,
        bg_opacity=bg_opacity,
        border_radius=border_radius,
        pad_x=pad_x,
        pad_y=pad_y,
        align=align,
        max_width_px=max_w,
        max_height_px=1200,
        enable_shadow=shadow
    )

    temp_path = UPLOAD_DIR / "temp_preview.png"
    img.save(temp_path, "PNG")
    return send_file(temp_path, mimetype="image/png")

@app.route("/api/workspace-videos")
def get_workspace_videos():
    """Return empty list - no default videos on startup."""
    return jsonify({"success": True, "clips": []})

@app.route("/api/capabilities")
def get_capabilities():
    """Report optional capabilities such as embedded AI upscaler."""
    return jsonify({
        "ai_upscale_available": bool(REALESRGAN_EXE)
    })

@app.route("/api/export", methods=["POST"])
def start_export():
    """Trigger async video concatenation and text overlay rendering (single or batch by N)."""
    data = request.json or {}
    clips = data.get("clips", [])
    text_overlays = data.get("overlays", [])
    canvas_mode = data.get("canvas_mode", "auto")
    fit_mode = data.get("fit_mode", "contain")
    custom_w = int(data.get("custom_w", 0))
    custom_h = int(data.get("custom_h", 0))
    try:
        volume = max(0.0, min(5.0, float(data.get("volume", 1.0))))
    except (TypeError, ValueError):
        volume = 1.0
    try:
        speed = max(0.25, min(4.0, float(data.get("speed", 1.0))))
    except (TypeError, ValueError):
        speed = 1.0
    crf_quality = int(data.get("crf", 0))
    upscale_mode = data.get("upscale_mode", "none")  # "none", "fast", "ai"
    if upscale_mode not in ("none", "fast", "ai"):
        upscale_mode = "none"
    merge_mode = data.get("merge_mode", "single") # "single" or "batch"
    chunk_size = max(1, int(data.get("chunk_size", 2)))
    handle_remainder = data.get("handle_remainder", "merge") # "merge" or "skip"

    if not clips:
        return jsonify({"error": "Vui lòng thêm ít nhất một video để ghép"}), 400

    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Đang khởi tạo tiến trình...",
        "output_url": None,
        "output_path": None,
        "outputs": [],
        "total_outputs": 1,
        "error": None
    }

    file_prefix = data.get("file_prefix", "export_final").strip() or "export_final"

    t = threading.Thread(
        target=process_export_task,
        args=(task_id, clips, text_overlays, canvas_mode, fit_mode, crf_quality, merge_mode, chunk_size, handle_remainder, file_prefix, custom_w, custom_h, volume, upscale_mode, speed)
    )
    t.daemon = True
    t.start()

    return jsonify({"success": True, "task_id": task_id})

def build_volume_filter(volume):
    """ffmpeg audio filter for a volume multiplier (limiter added when boosting to avoid clipping)."""
    if volume > 1.0:
        return f"volume={volume:.3f},alimiter=limit=0.98"
    return f"volume={volume:.3f}"


def build_atempo_filter(speed):
    """Chain ffmpeg atempo filters in [0.5, 2.0] to support any speed from 0.25x to 4.0x."""
    s = float(speed)
    parts = []
    while s > 2.0:
        parts.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        parts.append("atempo=0.5")
        s /= 0.5
    parts.append(f"atempo={s:.4f}")
    return ",".join(parts)


def upscale_clip_with_ai(input_path, output_path, progress_callback=None):
    """Upscale a single video clip 4x using embedded realesrgan-ncnn-vulkan + ffmpeg."""
    if not REALESRGAN_EXE:
        return False

    info = get_video_info(input_path)
    out_fps = fps_to_ffmpeg(info["fps"]) if info["fps"] > 0 else "30"
    work_dir = UPLOAD_DIR / f"ai_up_{uuid.uuid4().hex[:8]}"
    in_dir = work_dir / "in"
    out_dir = work_dir / "out"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        if progress_callback:
            progress_callback(2, "Đang tách khung hình để AI tăng nét...")

        extract_cmd = [
            FFMPEG_EXE, "-y", "-i", str(input_path),
            "-qscale:v", "2",
            str(in_dir / "frame_%08d.jpg")
        ]
        p_ext = subprocess.run(
            extract_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore",
            **SUBPROCESS_KWARGS
        )
        if p_ext.returncode != 0:
            return False

        total_frames = len(list(in_dir.glob("*.jpg")))
        if total_frames == 0:
            return False

        model_name = pick_realesrgan_model(REALESRGAN_MODELS_DIR)
        # Note: realesr-animevideov3-x4 is named realesr-animevideov3 in -n flag
        cli_model = "realesr-animevideov3" if model_name.startswith("realesr-animevideov3") else model_name

        ai_cmd = [
            REALESRGAN_EXE,
            "-i", str(in_dir),
            "-o", str(out_dir),
            "-n", cli_model,
            "-s", "4",
            "-f", "jpg",
        ]
        if REALESRGAN_MODELS_DIR:
            ai_cmd.extend(["-m", REALESRGAN_MODELS_DIR])

        proc = subprocess.Popen(
            ai_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="ignore", **SUBPROCESS_KWARGS
        )
        while proc.poll() is None:
            done_frames = len(list(out_dir.glob("*.jpg")))
            pct = min(85, 5 + int((done_frames / total_frames) * 80))
            if progress_callback:
                progress_callback(pct, f"AI đang tăng nét: {done_frames}/{total_frames} khung hình ({pct}%)")
            time.sleep(0.5)

        if proc.returncode != 0:
            return False

        if progress_callback:
            progress_callback(88, "Đang ghép khung hình AI thành video...")

        rebuild_cmd = [
            FFMPEG_EXE, "-y",
            "-framerate", out_fps,
            "-i", str(out_dir / "frame_%08d.jpg"),
            "-i", str(input_path),
            "-map", "0:v:0",
            "-map", "1:a?",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "14",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(output_path)
        ]
        p_reb = subprocess.run(
            rebuild_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore",
            **SUBPROCESS_KWARGS
        )
        return p_reb.returncode == 0 and Path(output_path).exists()
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def render_one_merged_clip(task_id, chunk_clips, overlays, canvas_mode, fit_mode, crf, output_file, part_num=1, total_parts=1, custom_w=0, custom_h=0, progress_callback=None, volume=1.0, upscale_mode="none", status_callback=None, speed=1.0):
    """Render a single merged video from a list of clips with text overlays."""
    has_speed = abs(speed - 1.0) > 0.001
    # Target resolution: user custom dimensions take highest priority
    target_w = 720
    target_h = 1280

    if custom_w > 0 and custom_h > 0:
        target_w = custom_w
        target_h = custom_h
    elif canvas_mode == "auto":
        first_info = get_video_info(chunk_clips[0]["path"])
        target_w = first_info["width"]
        target_h = first_info["height"]
    elif canvas_mode == "9:16":
        target_w = 1080
        target_h = 1920
    elif canvas_mode == "16:9":
        target_w = 1920
        target_h = 1080
    elif canvas_mode == "1:1":
        target_w = 1080
        target_h = 1080

    # Ensure even dimensions for H.264 video codec
    if target_w % 2 != 0:
        target_w += 1
    if target_h % 2 != 0:
        target_h += 1

    total_duration = sum(float(c.get("duration", 0)) for c in chunk_clips)
    if total_duration <= 0:
        total_duration = 10.0
    if has_speed:
        total_duration = max(0.1, total_duration / speed)

    # Generate overlay PNG images with dynamic tag replacement
    overlay_images = []
    for idx, ov in enumerate(overlays):
        raw_text = ov.get("text", "")
        # Replace template placeholders {index}, {part}, {tap}, {phan}
        text = raw_text.replace("{index}", str(part_num))\
                       .replace("{part}", str(part_num))\
                       .replace("{tap}", str(part_num))\
                       .replace("{phan}", str(part_num))
        if not text.strip():
            continue

        # USER REQUIREMENT: Respect exact font size, and only auto-shrink when exceeding frame!
        font_size = max(10, int(float(ov.get("font_size", 42))))
        pad_x = max(2, int(float(ov.get("pad_x", 26))))
        pad_y = max(2, int(float(ov.get("pad_y", 14))))
        border_radius = max(0, int(float(ov.get("border_radius", 14))))
        max_width_px = int(target_w * (float(ov.get("max_width_pct", 85)) / 100.0))
        max_height_px = int(target_h * 0.9)

        img, img_w, img_h = create_text_badge_image(
            text=text,
            font_family=ov.get("font_family", "BeVietnamPro"),
            font_size=font_size,
            text_color=ov.get("text_color", "#000000"),
            bg_color=ov.get("bg_color", "#FFFFFF"),
            bg_opacity=float(ov.get("bg_opacity", 1.0)),
            border_radius=border_radius,
            pad_x=pad_x,
            pad_y=pad_y,
            align=ov.get("align", "center"),
            max_width_px=max_width_px,
            max_height_px=max_height_px,
            enable_shadow=bool(ov.get("shadow", True))
        )

        png_path = UPLOAD_DIR / f"badge_{task_id}_{part_num}_{idx}.png"
        img.save(png_path, "PNG")

        overlay_images.append({
            "path": str(png_path),
            "width": img_w,
            "height": img_h,
            "x_pct": float(ov.get("x_pct", 50.0)),
            "y_pct": float(ov.get("y_pct", 80.0)),
            "start": float(ov.get("start", 0.0)),
            "end": float(ov.get("end", total_duration)) if not ov.get("full_duration", True) else total_duration,
            "full_duration": ov.get("full_duration", True)
        })

    def run_ffmpeg(ff_cmd):
        proc = subprocess.Popen(
            ff_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore",
            **SUBPROCESS_KWARGS
        )
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line and "out_time_us=" in line:
                try:
                    us = int(line.split("=")[1].strip())
                    cur_sec = us / 1000000.0
                    clip_pct = min(99, int((cur_sec / total_duration) * 100))
                    if progress_callback:
                        progress_callback(clip_pct, cur_sec, total_duration)
                except Exception:
                    pass
        proc.wait()
        return proc.returncode == 0 and output_file.exists()

    clip_infos = [get_video_info(c["path"]) for c in chunk_clips]
    has_trim = any(float(c.get("trim_start", 0) or 0) > 0 or float(c.get("trim_end", 0) or 0) > 0 for c in chunk_clips)
    orig_upscale_flags = [info["width"] < target_w or info["height"] < target_h for info in clip_infos]
    any_upscaled = any(orig_upscale_flags)
    effective_clips = [dict(c) for c in chunk_clips]
    temp_ai_files = []

    if upscale_mode == "ai" and REALESRGAN_EXE and any_upscaled:
        ai_targets = [idx for idx, need in enumerate(orig_upscale_flags) if need]
        for pos, idx in enumerate(ai_targets):
            temp_ai_mp4 = UPLOAD_DIR / f"ai_clip_{task_id}_{part_num}_{idx}.mp4"
            def on_ai_prog(pct, msg, _pos=pos, _total=len(ai_targets)):
                if status_callback:
                    status_callback(f"[Clip {_pos + 1}/{_total}] {msg}", pct)
            if upscale_clip_with_ai(effective_clips[idx]["path"], temp_ai_mp4, progress_callback=on_ai_prog):
                temp_ai_files.append(temp_ai_mp4)
                effective_clips[idx]["path"] = str(temp_ai_mp4)
                clip_infos[idx] = get_video_info(str(temp_ai_mp4))

    success = False

    # 1) Lossless path: no text overlay and identical clip encoding -> join without re-encoding
    if crf <= 0 and upscale_mode == "none" and not has_speed and not has_trim and not overlay_images and can_stream_copy(clip_infos, target_w, target_h):
        list_path = UPLOAD_DIR / f"concat_{task_id}_{part_num}.txt"
        try:
            with open(list_path, "w", encoding="utf-8") as lf:
                for c in effective_clips:
                    p = str(Path(c["path"]).resolve()).replace("\\", "/").replace("'", "'\\''")
                    lf.write(f"file '{p}'\n")
            has_vol = abs(volume - 1.0) > 0.001
            if has_vol:
                # Video stays untouched; only audio is re-encoded with the new volume
                a_kb = max((i["a_kbps"] for i in clip_infos), default=0) or 192
                audio_args = ["-c:a", "aac", "-b:a", f"{a_kb}k", "-af", build_volume_filter(volume)]
            else:
                audio_args = ["-c:a", "copy"]
            copy_cmd = [
                FFMPEG_EXE, "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
                "-map", "0:v:0", "-map", "0:a?",
                "-c:v", "copy",
                *audio_args,
                "-movflags", "+faststart",
                "-progress", "pipe:1",
                str(output_file)
            ]
            success = run_ffmpeg(copy_cmd)
        except Exception:
            success = False
        finally:
            try:
                os.remove(list_path)
            except Exception:
                pass

    # 2) Re-encode path: keep source fps, audio sample rate and bitrates
    if not success:
        first = clip_infos[0]
        out_fps = fps_to_ffmpeg(first["fps"]) if first["fps"] > 0 else "30"
        out_a_rate = first["a_rate"] or 44100
        out_v_kbps = max((i["v_kbps"] for i in clip_infos), default=0)
        out_a_kbps = max((i["a_kbps"] for i in clip_infos), default=0) or 192

        cmd = [FFMPEG_EXE, "-y"]
        for clip in effective_clips:
            t_start = float(clip.get("trim_start", 0) or 0)
            t_end = float(clip.get("trim_end", 0) or 0)
            if t_start > 0:
                cmd.extend(["-ss", f"{t_start:.3f}"])
            if t_end > 0 and t_end > t_start:
                cmd.extend(["-to", f"{t_end:.3f}"])
            cmd.extend(["-i", clip["path"]])
        for ov_item in overlay_images:
            cmd.extend(["-i", ov_item["path"]])

        filter_parts = []
        concat_inputs = []

        for i, clip in enumerate(effective_clips):
            scale_flags = ":flags=lanczos" if upscale_mode != "none" else ""
            sharpen = ",cas=0.45" if (upscale_mode == "fast" and orig_upscale_flags[i]) else ""
            pts_prefix = f"setpts=PTS/{speed:.6f}," if has_speed else ""
            if fit_mode == "stretch":
                v_filter = f"[{i}:v]{pts_prefix}scale={target_w}:{target_h}{scale_flags}{sharpen},setsar=1,fps={out_fps}[v{i}];"
            elif fit_mode == "cover":
                v_filter = f"[{i}:v]{pts_prefix}scale={target_w}:{target_h}:force_original_aspect_ratio=increase{scale_flags},crop={target_w}:{target_h}{sharpen},setsar=1,fps={out_fps}[v{i}];"
            else:
                v_filter = f"[{i}:v]{pts_prefix}scale={target_w}:{target_h}:force_original_aspect_ratio=decrease{scale_flags}{sharpen},pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps={out_fps}[v{i}];"
            filter_parts.append(v_filter)

            clip_info = clip_infos[i]
            if clip_info["has_audio"]:
                tempo_suffix = f",{build_atempo_filter(speed)}" if has_speed else ""
                a_filter = f"[{i}:a]aformat=sample_fmts=fltp:sample_rates={out_a_rate}:channel_layouts=stereo{tempo_suffix}[a{i}];"
            else:
                dur = clip_info["duration"] if clip_info["duration"] > 0 else 5.0
                if has_speed:
                    dur = max(0.05, dur / speed)
                a_filter = f"aevalsrc=0:d={dur:.3f}:s={out_a_rate}[a{i}];"
            filter_parts.append(a_filter)

            concat_inputs.append(f"[v{i}][a{i}]")

        num_clips = len(chunk_clips)
        filter_parts.append(f"{''.join(concat_inputs)}concat=n={num_clips}:v=1:a=1[vcat][acat];")

        current_v = "[vcat]"
        for j, ov_item in enumerate(overlay_images):
            badge_input_idx = num_clips + j
            next_v = f"[vov{j}]" if j < len(overlay_images) - 1 else "[vout]"

            bw = ov_item["width"]
            bh = ov_item["height"]

            x_pos = int((target_w * (ov_item["x_pct"] / 100.0)) - (bw / 2.0))
            y_pos = int((target_h * (ov_item["y_pct"] / 100.0)) - (bh / 2.0))

            x_pos = max(0, min(target_w - bw, x_pos))
            y_pos = max(0, min(target_h - bh, y_pos))

            if ov_item["full_duration"]:
                enable_clause = ""
            else:
                enable_clause = f":enable='between(t,{ov_item['start']},{ov_item['end']})'"

            filter_parts.append(f"{current_v}[{badge_input_idx}:v]overlay=x={x_pos}:y={y_pos}{enable_clause}{next_v};")
            current_v = next_v

        final_video_label = current_v if overlay_images else "[vcat]"
        final_audio_label = "[acat]"
        if abs(volume - 1.0) > 0.001:
            filter_parts.append(f"[acat]{build_volume_filter(volume)}[aout];")
            final_audio_label = "[aout]"
        filter_complex_str = "".join(filter_parts).rstrip(";")

        # Match the source video bitrate when known; otherwise fall back to CRF quality
        # crf <= 0: match source bitrate (unless upscaling, which needs higher bitrate / CRF 18)
        if crf <= 0 and out_v_kbps > 0 and not (any_upscaled and upscale_mode != "none"):
            v_rate_args = ["-b:v", f"{out_v_kbps}k", "-maxrate", f"{int(out_v_kbps * 1.5)}k", "-bufsize", f"{out_v_kbps * 2}k"]
        else:
            v_rate_args = ["-crf", str(crf if crf > 0 else (18 if (any_upscaled and upscale_mode != "none") else 22))]

        cmd.extend([
            "-filter_complex", filter_complex_str,
            "-map", final_video_label,
            "-map", final_audio_label,
            "-c:v", "libx264",
            "-preset", "medium",
            *v_rate_args,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", f"{out_a_kbps}k",
            "-ar", str(out_a_rate),
            "-movflags", "+faststart",
            "-progress", "pipe:1",
            str(output_file)
        ])

        success = run_ffmpeg(cmd)

    # Clean up temporary badge PNGs and AI upscaled temp clips
    for ov_item in overlay_images:
        try:
            os.remove(ov_item["path"])
        except Exception:
            pass
    for tmp_f in temp_ai_files:
        try:
            os.remove(tmp_f)
        except Exception:
            pass

    return success


def process_export_task(task_id, clips, overlays, canvas_mode, fit_mode, crf, merge_mode, chunk_size, handle_remainder, file_prefix="export_final", custom_w=0, custom_h=0, volume=1.0, upscale_mode="none", speed=1.0):
    """Background rendering worker handling single merge or batch N-clip merging."""
    try:
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["progress"] = 2
        tasks[task_id]["message"] = "Đang chuẩn bị danh sách video..."

        # Partition clips into chunks
        if merge_mode == "batch" and chunk_size >= 1:
            chunks = [clips[i:i + chunk_size] for i in range(0, len(clips), chunk_size)]
            if handle_remainder == "skip" and len(chunks) > 1 and len(chunks[-1]) < chunk_size:
                chunks.pop()
        else:
            chunks = [clips]

        total_chunks = len(chunks)
        tasks[task_id]["total_outputs"] = total_chunks
        outputs_list = []

        if not file_prefix:
            file_prefix = "export_final"

        for idx, chunk_clips in enumerate(chunks):
            part_num = idx + 1
            filename = f"{part_num}_{file_prefix}.mp4"
            
            output_file = OUTPUT_DIR / filename
            # If file already exists, avoid collision by appending timestamp only if necessary
            if output_file.exists():
                filename = f"{part_num}_{file_prefix}_{int(time.time())}.mp4"
                output_file = OUTPUT_DIR / filename

            def on_progress(clip_pct, cur_sec, total_dur):
                # Calculate overall progress across all chunks
                base_pct = (idx / total_chunks) * 100
                chunk_contribution = (clip_pct / total_chunks)
                overall_pct = min(98, int(base_pct + chunk_contribution))
                tasks[task_id]["progress"] = overall_pct
                if total_chunks > 1:
                    tasks[task_id]["message"] = f"Đang xuất video {part_num}/{total_chunks} (gồm {len(chunk_clips)} clip): {int(cur_sec)}s / {int(total_dur)}s ({overall_pct}%)"
                else:
                    tasks[task_id]["message"] = f"Đang xuất video: {int(cur_sec)}s / {int(total_dur)}s ({overall_pct}%)"

            def on_status(msg, pct):
                base_pct = (idx / total_chunks) * 100
                overall_pct = min(98, int(base_pct + (pct * 0.5 / total_chunks)))
                tasks[task_id]["progress"] = overall_pct
                tasks[task_id]["message"] = msg

            success = render_one_merged_clip(
                task_id=task_id,
                chunk_clips=chunk_clips,
                overlays=overlays,
                canvas_mode=canvas_mode,
                fit_mode=fit_mode,
                crf=crf,
                output_file=output_file,
                part_num=part_num,
                total_parts=total_chunks,
                custom_w=custom_w,
                custom_h=custom_h,
                volume=volume,
                upscale_mode=upscale_mode,
                speed=speed,
                progress_callback=on_progress,
                status_callback=on_status
            )

            if not success:
                tasks[task_id]["status"] = "failed"
                tasks[task_id]["error"] = f"Lỗi khi xuất video phần {part_num}/{total_chunks}"
                return

            outputs_list.append({
                "part": part_num,
                "name": filename,
                "url": f"/outputs/{filename}",
                "path": str(output_file),
                "clip_count": len(chunk_clips),
                "duration": round(sum(float(c.get("duration", 0)) for c in chunk_clips) / (speed if abs(speed - 1.0) > 0.001 else 1.0), 2)
            })

        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        if total_chunks > 1:
            tasks[task_id]["message"] = f"Xuất thành công tất cả {total_chunks} video riêng biệt!"
        else:
            tasks[task_id]["message"] = "Xuất video hoàn tất thành công!"

        tasks[task_id]["outputs"] = outputs_list
        tasks[task_id]["output_url"] = outputs_list[0]["url"]
        tasks[task_id]["output_path"] = outputs_list[0]["path"]

    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)

@app.route("/api/progress/<task_id>")
def get_task_progress(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Không tìm thấy tiến trình"}), 404
    return jsonify(task)

@app.route("/api/open-folder", methods=["POST"])
def open_output_folder():
    """Open output folder in native file manager (Windows Explorer, macOS Finder, or Linux)."""
    try:
        data = request.json or {}
        filepath = data.get("path")
        if sys.platform == "darwin":
            if filepath and os.path.exists(filepath):
                subprocess.run(["open", "-R", str(Path(filepath).resolve())])
            else:
                subprocess.run(["open", str(OUTPUT_DIR.resolve())])
        elif sys.platform == "win32":
            if filepath and os.path.exists(filepath):
                subprocess.run(["explorer.exe", "/select,", os.path.normpath(filepath)], **SUBPROCESS_KWARGS)
            else:
                subprocess.run(["explorer.exe", os.path.normpath(str(OUTPUT_DIR))], **SUBPROCESS_KWARGS)
        else:
            if filepath and os.path.exists(filepath):
                subprocess.run(["xdg-open", str(Path(filepath).parent)])
            else:
                subprocess.run(["xdg-open", str(OUTPUT_DIR)])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/outputs/<filename>")
def serve_output(filename):
    return send_from_directory(OUTPUT_DIR, filename)


# =====================================================================
# WEBHOOK & AUTOMATION REST API (/api/v1/* and /api/webhook/*)
# =====================================================================

def _run_api_job(job):
    """Execute one queued API video edit job (downloads URLs if needed, renders, fires webhook)."""
    task_id = job["task_id"]
    downloaded_files = []
    try:
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["progress"] = 2
        tasks[task_id]["message"] = "Đang chuẩn bị nguồn video từ API..."

        resolved_clips = []
        for idx, raw_clip in enumerate(job["raw_clips"]):
            if isinstance(raw_clip, str):
                src = raw_clip.strip()
                t_start, t_end = 0.0, 0.0
            elif isinstance(raw_clip, dict):
                src = str(raw_clip.get("source") or raw_clip.get("path") or raw_clip.get("url") or "").strip()
                t_start = max(0.0, float(raw_clip.get("trim_start", 0) or 0))
                t_end = max(0.0, float(raw_clip.get("trim_end", 0) or 0))
            else:
                continue

            if not src:
                continue

            if src.lower().startswith(("http://", "https://")):
                tasks[task_id]["message"] = f"Đang tải video {idx + 1}/{len(job['raw_clips'])} từ URL..."
                ext = Path(src.split("?")[0]).suffix or ".mp4"
                local_tmp = UPLOAD_DIR / f"api_dl_{task_id}_{idx}{ext}"
                download_remote_video(src, local_tmp)
                downloaded_files.append(local_tmp)
                local_path = str(local_tmp)
            else:
                if not os.path.exists(src):
                    raise FileNotFoundError(f"Không tìm thấy file video: {src}")
                local_path = src

            info = get_video_info(local_path)
            dur = info["duration"]
            if t_end > t_start > 0:
                dur = t_end - t_start
            elif t_end > 0:
                dur = min(dur, t_end)
            elif t_start > 0:
                dur = max(0.1, dur - t_start)

            resolved_clips.append({
                "path": local_path,
                "duration": dur,
                "trim_start": t_start,
                "trim_end": t_end,
            })

        if not resolved_clips:
            raise ValueError("Danh sách clips hợp lệ bị rỗng")

        process_export_task(
            task_id=task_id,
            clips=resolved_clips,
            overlays=job["overlays"],
            canvas_mode=job["canvas_mode"],
            fit_mode=job["fit_mode"],
            crf=job["crf"],
            merge_mode=job["merge_mode"],
            chunk_size=job["chunk_size"],
            handle_remainder=job["handle_remainder"],
            file_prefix=job["file_prefix"],
            custom_w=job["custom_w"],
            custom_h=job["custom_h"],
            volume=job["volume"],
            upscale_mode=job["upscale_mode"],
            speed=job["speed"],
        )

        # Attach full download URLs for external callers
        base_url = f"http://127.0.0.1:{SERVER_PORT}"
        for out in tasks[task_id].get("outputs", []):
            out["download_url"] = f"{base_url}{out['url']}"
            if os.path.exists(out["path"]):
                out["size_bytes"] = os.path.getsize(out["path"])

        if job.get("webhook_url"):
            send_webhook_callback(job["webhook_url"], {
                "task_id": task_id,
                "status": tasks[task_id]["status"],
                "outputs": tasks[task_id].get("outputs", []),
                "error": tasks[task_id].get("error"),
            })
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["message"] = f"Lỗi: {e}"
        if job.get("webhook_url"):
            send_webhook_callback(job["webhook_url"], {
                "task_id": task_id,
                "status": "failed",
                "error": str(e),
            })
    finally:
        for tmp_f in downloaded_files:
            try:
                if tmp_f.exists():
                    os.remove(tmp_f)
            except Exception:
                pass


def _api_worker_loop():
    while True:
        job = api_job_queue.get()
        try:
            _run_api_job(job)
        finally:
            api_job_queue.task_done()


def ensure_api_worker():
    global _api_worker_started
    if not _api_worker_started:
        _api_worker_started = True
        t = threading.Thread(target=_api_worker_loop, daemon=True)
        t.start()


@app.route("/api/webhook/config", methods=["GET", "POST"])
def webhook_config_route():
    """Internal UI endpoint to view or update Webhook API settings."""
    cfg = load_api_config()
    if request.method == "POST":
        data = request.json or {}
        if "api_enabled" in data:
            cfg["api_enabled"] = bool(data["api_enabled"])
        if "retention_hours" in data:
            try:
                cfg["retention_hours"] = max(0, int(data["retention_hours"]))
            except (TypeError, ValueError):
                pass
        if data.get("regenerate_key"):
            cfg["api_key"] = f"mvt_{secrets.token_hex(20)}"
        save_api_config(cfg)

    return jsonify({
        "api_enabled": cfg.get("api_enabled", True),
        "api_key": cfg.get("api_key", ""),
        "port": SERVER_PORT,
        "base_url": f"http://127.0.0.1:{SERVER_PORT}",
        "retention_hours": cfg.get("retention_hours", 0),
        "queue_size": api_job_queue.qsize(),
        "storage": get_output_storage_stats(),
    })


@app.route("/api/webhook/cleanup", methods=["POST"])
def webhook_cleanup_route():
    """Delete files in OUTPUT_DIR (all or older than retention_hours)."""
    data = request.json or {}
    hours = int(data.get("older_than_hours", 0) or 0)
    cutoff = time.time() - (hours * 3600) if hours > 0 else None
    deleted = 0
    for p in OUTPUT_DIR.glob("*"):
        if p.is_file():
            if cutoff is None or p.stat().st_mtime < cutoff:
                try:
                    os.remove(p)
                    deleted += 1
                except Exception:
                    pass
    return jsonify({"success": True, "deleted": deleted, "storage": get_output_storage_stats()})


@app.route("/api/v1/health", methods=["GET"])
def api_v1_health():
    cfg = load_api_config()
    return jsonify({
        "status": "ok" if cfg.get("api_enabled", True) else "disabled",
        "service": "MergeVideoTool",
        "ai_upscale_available": bool(REALESRGAN_EXE),
        "queue_size": api_job_queue.qsize(),
    })


@app.route("/api/v1/video/edit", methods=["POST"])
@require_api_key
def api_v1_video_edit():
    """Queue an automated video edit job (merge, trim, text overlays, speed, volume, upscale)."""
    ensure_api_worker()
    data = request.json or {}
    raw_clips = data.get("clips", [])
    if not raw_clips or not isinstance(raw_clips, list):
        return jsonify({"error": "Field 'clips' must be a non-empty array of paths, URLs, or objects"}), 400

    try:
        volume = max(0.0, min(5.0, float(data.get("volume", 1.0))))
    except (TypeError, ValueError):
        volume = 1.0
    try:
        speed = max(0.25, min(4.0, float(data.get("speed", 1.0))))
    except (TypeError, ValueError):
        speed = 1.0

    upscale_mode = data.get("upscale_mode", "none")
    if upscale_mode not in ("none", "fast", "ai"):
        upscale_mode = "none"

    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Đang chờ trong hàng đợi API...",
        "output_url": None,
        "output_path": None,
        "outputs": [],
        "total_outputs": 1,
        "error": None,
    }

    job = {
        "task_id": task_id,
        "raw_clips": raw_clips,
        "overlays": data.get("overlays", []),
        "canvas_mode": data.get("canvas_mode", "auto"),
        "fit_mode": data.get("fit_mode", "contain"),
        "custom_w": int(data.get("width", data.get("custom_w", 0)) or 0),
        "custom_h": int(data.get("height", data.get("custom_h", 0)) or 0),
        "crf": int(data.get("crf", 0) or 0),
        "volume": volume,
        "speed": speed,
        "upscale_mode": upscale_mode,
        "merge_mode": data.get("merge_mode", "single"),
        "chunk_size": max(1, int(data.get("chunk_size", 2) or 2)),
        "handle_remainder": data.get("handle_remainder", "merge"),
        "file_prefix": (str(data.get("file_prefix", "api_export")).strip() or "api_export"),
        "webhook_url": str(data.get("webhook_url", "") or "").strip(),
    }
    api_job_queue.put(job)

    base_url = f"http://127.0.0.1:{SERVER_PORT}"
    return jsonify({
        "success": True,
        "task_id": task_id,
        "status": "queued",
        "queue_size": api_job_queue.qsize(),
        "status_url": f"{base_url}/api/v1/status/{task_id}",
        "result_url": f"{base_url}/api/v1/result/{task_id}",
    }), 202


@app.route("/api/v1/status/<task_id>", methods=["GET"])
@require_api_key
def api_v1_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify({
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "message": task["message"],
        "outputs": task.get("outputs", []),
        "error": task.get("error"),
    })


@app.route("/api/v1/result/<task_id>", methods=["GET"])
@require_api_key
def api_v1_result(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    if task["status"] != "completed":
        return jsonify({"task_id": task_id, "status": task["status"], "error": task.get("error")}), 409

    if request.args.get("download") == "1" and task.get("output_path") and os.path.exists(task["output_path"]):
        return send_file(task["output_path"], as_attachment=True)

    return jsonify({
        "task_id": task_id,
        "status": "completed",
        "outputs": task.get("outputs", []),
    })


@app.route("/api/v1/docs", methods=["GET"])
def api_v1_docs():
    """Return interactive HTML or JSON (?format=json) API documentation."""
    base_url = f"http://127.0.0.1:{SERVER_PORT}"
    schema = {
        "service": "MergeVideoTool Webhook API",
        "base_url": base_url,
        "auth_header": "X-API-Key: <your_api_key>",
        "endpoints": {
            "health": f"GET {base_url}/api/v1/health",
            "edit_video": f"POST {base_url}/api/v1/video/edit",
            "check_status": f"GET {base_url}/api/v1/status/{{task_id}}",
            "get_result": f"GET {base_url}/api/v1/result/{{task_id}} (?download=1)",
        },
        "example_payload": {
            "clips": [
                {"source": "C:/videos/clip1.mp4", "trim_start": 0, "trim_end": 5},
                {"source": "https://example.com/clip2.mp4"},
            ],
            "width": 1080,
            "height": 1920,
            "fit_mode": "contain",
            "speed": 1.25,
            "volume": 1.0,
            "upscale_mode": "none",
            "crf": 18,
            "file_prefix": "auto_tiktok",
            "overlays": [
                {
                    "text": "Tap {index} - Review san pham",
                    "font_size": 42,
                    "x_pct": 50,
                    "y_pct": 80,
                    "text_color": "#000000",
                    "bg_color": "#FFFFFF",
                    "full_duration": True,
                }
            ],
            "webhook_url": "http://localhost:5678/webhook/video-done",
        },
    }
    if request.args.get("format") == "json":
        return jsonify(schema)

    pretty_json = json.dumps(schema["example_payload"], indent=2, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>MergeVideoTool Webhook API Docs</title>
<style>
body{{font-family:system-ui,sans-serif;background:#0b0f19;color:#e2e8f0;max-width:920px;margin:32px auto;padding:0 20px;line-height:1.6}}
h1,h2{{color:#38bdf8}} code,pre{{background:#111827;border:1px solid #1e293b;border-radius:8px;padding:2px 6px}}
pre{{padding:14px;overflow:auto}} .tag{{display:inline-block;background:#0ea5e9;color:#082f49;font-weight:700;padding:2px 8px;border-radius:6px;font-size:12px}}
</style></head><body>
<h1>MergeVideoTool Webhook API v1</h1>
<p>Base URL: <code>{base_url}</code> · Auth Header: <code>X-API-Key: &lt;API_KEY&gt;</code> · <a href="?format=json" style="color:#38bdf8">Xem JSON Schema</a></p>
<h2>1. Endpoints</h2>
<ul>
  <li><span class="tag">GET</span> <code>/api/v1/health</code> — Kiểm tra trạng thái server &amp; hàng đợi</li>
  <li><span class="tag">POST</span> <code>/api/v1/video/edit</code> — Gửi job dựng video tự động (trả về <code>task_id</code>)</li>
  <li><span class="tag">GET</span> <code>/api/v1/status/{{task_id}}</code> — Kiểm tra tiến độ (%) và trạng thái</li>
  <li><span class="tag">GET</span> <code>/api/v1/result/{{task_id}}</code> — Lấy JSON kết quả (thêm <code>?download=1</code> để tải thẳng MP4)</li>
</ul>
<h2>2. Payload mẫu (POST /api/v1/video/edit)</h2>
<pre>{pretty_json}</pre>
<h2>3. Tham số hỗ trợ</h2>
<ul>
  <li><b>clips</b>: Mảng đường dẫn local hoặc URL <code>http(s)://</code>, hoặc object <code>{{"source", "trim_start", "trim_end"}}</code></li>
  <li><b>width / height</b>: Kích thước xuất (mặc định <code>0</code> = giữ theo video đầu hoặc <code>canvas_mode</code>)</li>
  <li><b>fit_mode</b>: <code>contain</code> | <code>cover</code> | <code>stretch</code></li>
  <li><b>speed</b>: <code>0.25</code> → <code>4.0</code> (mặc định <code>1.0</code>)</li>
  <li><b>volume</b>: <code>0.0</code> → <code>5.0</code> (mặc định <code>1.0</code>)</li>
  <li><b>upscale_mode</b>: <code>none</code> (tắt) | <code>fast</code> (Lanczos+CAS) | <code>ai</code> (Real-ESRGAN)</li>
  <li><b>merge_mode</b>: <code>single</code> | <code>batch</code> (kèm <code>chunk_size</code>, <code>handle_remainder</code>)</li>
  <li><b>webhook_url</b>: URL nhận POST tự động khi render xong (tùy chọn cho n8n/Make)</li>
</ul>
</body></html>"""
    return html


def run_flask_server(port, host="127.0.0.1"):
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    import socket

    parser = argparse.ArgumentParser(description="MergeVideoTool Desktop & Webhook API")
    parser.add_argument("--headless", action="store_true", help="Run only background Webhook API without GUI window")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=0, help="Port to listen on (default from config or 8765)")
    args, _ = parser.parse_known_args()

    cfg = load_api_config()
    port = args.port or int(cfg.get("port", 8765))

    # Check if preferred port is open, otherwise pick an available dynamic port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((args.host, port))
        s.close()
    except OSError:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((args.host, 0))
        port = s.getsockname()[1]
        s.close()

    SERVER_PORT = port
    ensure_api_worker()

    print("=" * 60)
    print(" [*] MergeVideoTool (Desktop + Webhook API)")
    print(f" [*] Local Server URL: http://{args.host}:{port}")
    print(f" [*] API Docs URL    : http://{args.host}:{port}/api/v1/docs")
    print("=" * 60)

    server_thread = threading.Thread(target=run_flask_server, args=(port, args.host), daemon=True)
    server_thread.start()

    if args.headless:
        server_thread.join()
    else:
        # Native Desktop Application Window (like Electron)
        try:
            import webview
            window = webview.create_window(
                title="MergeVideoTool",
                url=f"http://{args.host}:{port}",
                width=1340,
                height=860,
                min_size=(1080, 700),
                background_color="#0b0f19"
            )
            webview.start(debug=False)
        except Exception as e:
            print(f"Native window failed: {e}. Opening browser fallback...")
            def open_browser():
                time.sleep(1.0)
                webbrowser.open(f"http://{args.host}:{port}")
            threading.Thread(target=open_browser, daemon=True).start()
            server_thread.join()
