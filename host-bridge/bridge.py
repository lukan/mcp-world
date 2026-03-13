"""
host-bridge/bridge.py

Runs on the HOST machine (not in Docker).
Gives Docker containers access to screen capture and keyboard/mouse input.
Docker containers reach it via: http://host.docker.internal:5001

Environment variables:
  BRIDGE_WINDOW_TITLE  - partial window title to target (e.g. "EverQuest")
                         if not set, captures full desktop
  BRIDGE_CHAT_PREFIX   - if set, type_text will open chat first
  BRIDGE_CHAT_KEY      - key to open/send chat (default: enter)
  BRIDGE_PORT          - port to listen on (default: 5001)
"""

import base64
import io
import os
import time

import pyautogui
import pygetwindow as gw
from flask import Flask, jsonify, request
from mss import mss
from PIL import Image

app = Flask(__name__)

# Config
WINDOW_TITLE = os.environ.get("BRIDGE_WINDOW_TITLE", "").strip()
CHAT_PREFIX = os.environ.get("BRIDGE_CHAT_PREFIX", "").strip()
CHAT_KEY = os.environ.get("BRIDGE_CHAT_KEY", "enter").strip()
PORT = int(os.environ.get("BRIDGE_PORT", 5001))

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


# ---------------------------------------------------------------------------
# Window helpers
# ---------------------------------------------------------------------------

def find_window(title: str):
    """Return the first visible window whose title contains `title` (case-insensitive)."""
    title_lower = title.lower()
    for w in gw.getAllWindows():
        if title_lower in w.title.lower() and w.visible:
            return w
    return None


def get_target_window():
    """Return the configured target window, or None if not configured / not found."""
    if not WINDOW_TITLE:
        return None
    return find_window(WINDOW_TITLE)


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------

def capture_desktop() -> Image.Image:
    with mss() as sct:
        monitor = sct.monitors[1]  # primary monitor
        raw = sct.grab(monitor)
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


def capture_window(win) -> Image.Image:
    region = {
        "top": win.top,
        "left": win.left,
        "width": win.width,
        "height": win.height,
    }
    with mss() as sct:
        raw = sct.grab(region)
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


def image_to_base64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def action_key_press(key: str):
    pyautogui.press(key)


def action_key_hold(key: str, duration: float):
    pyautogui.keyDown(key)
    time.sleep(duration)
    pyautogui.keyUp(key)


def action_type_text(text: str):
    if CHAT_PREFIX:
        pyautogui.press(CHAT_KEY)
        time.sleep(0.15)
        pyautogui.typewrite(text, interval=0.03)
        time.sleep(0.05)
        pyautogui.press(CHAT_KEY)
    else:
        pyautogui.typewrite(text, interval=0.03)


def action_mouse_move(x: int, y: int):
    pyautogui.moveTo(x, y)


def action_mouse_click(x: int, y: int, button: str = "left"):
    pyautogui.click(x, y, button=button)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    win = get_target_window()
    status = {
        "status": "ok",
        "window_title_configured": WINDOW_TITLE or None,
        "window_found": win is not None,
        "window_info": None,
    }
    if win:
        status["window_info"] = {
            "title": win.title,
            "left": win.left,
            "top": win.top,
            "width": win.width,
            "height": win.height,
        }
    return jsonify(status)


@app.route("/screenshot")
def screenshot():
    try:
        win = get_target_window()
        if win:
            img = capture_window(win)
            source = "window"
        else:
            img = capture_desktop()
            source = "desktop"

        return jsonify({
            "image": image_to_base64(img),
            "format": "png",
            "source": source,
            "width": img.width,
            "height": img.height,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/action", methods=["POST"])
def action():
    data = request.get_json(force=True)
    if not data or "type" not in data:
        return jsonify({"error": "missing 'type' field"}), 400

    action_type = data["type"]

    try:
        if action_type == "key_press":
            action_key_press(data["key"])

        elif action_type == "key_hold":
            action_key_hold(data["key"], float(data.get("duration", 1.0)))

        elif action_type == "type_text":
            action_type_text(data["text"])

        elif action_type == "mouse_move":
            action_mouse_move(int(data["x"]), int(data["y"]))

        elif action_type == "mouse_click":
            action_mouse_click(
                int(data["x"]),
                int(data["y"]),
                data.get("button", "left"),
            )

        else:
            return jsonify({"error": f"unknown action type: {action_type}"}), 400

        return jsonify({"ok": True, "action": action_type})

    except KeyError as e:
        return jsonify({"error": f"missing required field: {e}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/window/list")
def window_list():
    windows = []
    for w in gw.getAllWindows():
        if w.visible and w.title.strip():
            windows.append({
                "title": w.title,
                "left": w.left,
                "top": w.top,
                "width": w.width,
                "height": w.height,
            })
    windows.sort(key=lambda w: w["title"].lower())
    return jsonify({"windows": windows})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"host-bridge starting on port {PORT}")
    if WINDOW_TITLE:
        print(f"  targeting window: '{WINDOW_TITLE}'")
        win = get_target_window()
        if win:
            print(f"  found: '{win.title}'")
        else:
            print(f"  WARNING: window not found — will capture full desktop until it appears")
    else:
        print("  no BRIDGE_WINDOW_TITLE set — capturing full desktop")
    if CHAT_PREFIX:
        print(f"  chat mode enabled (key: {CHAT_KEY})")
    print()
    app.run(host="0.0.0.0", port=PORT)
