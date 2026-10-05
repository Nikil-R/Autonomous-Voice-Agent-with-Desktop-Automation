"""
Native Windows Transparent Floating Desktop Notch HUD.
Runs directly on the user's desktop screen across all applications without ANY browser window or background!
- Borderless, semi-translucent titanium slate pill with rounded edges.
- Always on top (-topmost) with transparent background (-transparentcolor).
- Connects directly to FastAPI backend via WebSockets.
- Includes microphone listener with speech recognition and instant Edge-TTS voice playback.
- Press SPACE to speak, or click the mic button on the notch!
"""

import sys
import os
import json
import time
import base64
import asyncio
import threading
from pathlib import Path
import tkinter as tk
from tkinter import font

# Ensure ApexCore root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import requests
import sounddevice as sd
import soundfile as sf
import io

API_BASE = "http://127.0.0.1:8000"


class FloatingNotchHUD:
    """Native Windows Transparent Floating Dynamic Island HUD."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("VoiceAgent_Overlay")
        self.root.overrideredirect(True)       # Frameless / No Windows titlebar
        self.root.attributes("-topmost", True)  # Always floats on top of all windows
        self.transparent_key = "#000001"
        self.root.attributes("-transparentcolor", self.transparent_key)
        self.root.config(bg=self.transparent_key)

        # Center at the top of the monitor
        screen_w = self.root.winfo_screenwidth()
        notch_w = 480
        notch_h = 64
        x = (screen_w - notch_w) // 2
        y = 14
        self.root.geometry(f"{notch_w}x{notch_h}+{x}+{y}")

        self.status = "idle"  # idle, listening, thinking, speaking
        self.current_text = "Press Space or Click to Speak"
        self.is_listening = False
        self.audio_thread = None

        # Build Canvas
        self.canvas = tk.Canvas(
            self.root,
            width=notch_w,
            height=notch_h,
            bg=self.transparent_key,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        # Click event to toggle listen
        self.canvas.bind("<Button-1>", lambda e: self.toggle_voice())

        # Global Spacebar hotkey inside window
        self.root.bind("<space>", lambda e: self.toggle_voice())

        # Draggable window capability
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.do_drag)
        self.drag_x = 0
        self.drag_y = 0

        self.draw_notch()

    def start_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def do_drag(self, event):
        x = self.root.winfo_x() + (event.x - self.drag_x)
        y = self.root.winfo_y() + (event.y - self.drag_y)
        self.root.geometry(f"+{x}+{y}")

    def draw_notch(self):
        self.canvas.delete("all")
        w, h = 480, 64
        r = 22  # Corner radius

        # Color schemes based on status
        border_color = "#3a4253"
        fill_color = "#181c26"
        accent_color = "#818cf8"
        dot_color = "#64748b"

        if self.status == "listening":
            border_color = "#34d399"
            fill_color = "#152026"
            dot_color = "#34d399"
            accent_color = "#34d399"
        elif self.status == "thinking":
            border_color = "#fbbf24"
            fill_color = "#241f18"
            dot_color = "#fbbf24"
            accent_color = "#fbbf24"
        elif self.status == "speaking":
            border_color = "#38bdf8"
            fill_color = "#16232f"
            dot_color = "#38bdf8"
            accent_color = "#38bdf8"

        # Draw smooth rounded polygon
        pad = 4
        x1, y1 = pad, pad
        x2, y2 = w - pad, h - pad
        pts = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1
        ]
        self.canvas.create_polygon(pts, fill=fill_color, outline=border_color, width=1.5, smooth=True)

        # Draw glowing status dot
        self.canvas.create_oval(24, 26, 36, 38, fill=dot_color, outline="")

        # Draw brand label
        self.canvas.create_text(
            46, 24,
            text="VOICE AI",
            anchor="w",
            fill=accent_color,
            font=("Segoe UI", 8, "bold")
        )

        # Draw main state text
        display_text = self.current_text
        if len(display_text) > 42:
            display_text = display_text[:39] + "..."

        self.canvas.create_text(
            46, 40,
            text=display_text,
            anchor="w",
            fill="#e2e8f0",
            font=("Segoe UI", 10, "normal")
        )

        # Draw Hotkey pill at right
        self.canvas.create_rectangle(w - 75, 20, w - 20, 44, fill="#252c3b", outline="#3a4457", width=1)
        self.canvas.create_text(
            w - 47, 32,
            text="SPACE",
            fill="#94a3b8",
            font=("Segoe UI", 8, "bold")
        )

    def set_status(self, status: str, text: str):
        self.status = status
        self.current_text = text
        self.draw_notch()

    def toggle_voice(self):
        if self.is_listening:
            self.is_listening = False
            self.set_status("idle", "Press Space or Click to Speak")
        else:
            self.is_listening = True
            self.set_status("listening", "Listening... (Speak naturally)")
            threading.Thread(target=self._record_and_dispatch, daemon=True).start()

    def _record_and_dispatch(self):
        try:
            # Capture audio via SpeechRecognition or local Whisper
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 300
            recognizer.dynamic_energy_threshold = True

            with sr.Microphone(sample_rate=16000) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio_data = recognizer.listen(source, timeout=5, phrase_time_limit=10)

            self.root.after(0, lambda: self.set_status("thinking", "Right away, Sir..."))
            transcript = recognizer.recognize_google(audio_data)

            if not transcript.strip():
                self.root.after(0, lambda: self.set_status("idle", "Press Space or Click to Speak"))
                self.is_listening = False
                return

            self.root.after(0, lambda: self.set_status("thinking", f'"{transcript}"'))

            # Send to FastAPI /api/chat
            res = requests.post(f"{API_BASE}/api/chat", json={"prompt": transcript}, timeout=25)
            data = res.json()
            response_text = data.get("response", "")
            audio_b64 = data.get("audio_base64")

            self.root.after(0, lambda: self.set_status("speaking", response_text))

            # Play audio bytes
            if audio_b64:
                audio_bytes = base64.b64decode(audio_b64)
                data_np, sr_val = sf.read(io.BytesIO(audio_bytes))
                sd.play(data_np, sr_val)
                sd.wait()

            self.root.after(1000, lambda: self.set_status("idle", "Press Space or Click to Speak"))
            self.is_listening = False

        except Exception as e:
            err_msg = str(e)
            if "WaitTimeoutError" in err_msg:
                self.root.after(0, lambda: self.set_status("idle", "Press Space to Speak"))
            else:
                self.root.after(0, lambda: self.set_status("idle", "Error: " + err_msg[:25]))
            self.is_listening = False


def launch_native_floating_notch():
    """Starts the native transparent desktop notch HUD."""
    app = FloatingNotchHUD()
    app.root.mainloop()


if __name__ == "__main__":
    launch_native_floating_notch()
