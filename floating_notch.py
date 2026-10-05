"""
Native Windows Transparent Floating Desktop Notch HUD.
Runs directly on the user's desktop screen across all applications without ANY browser window or background!
- Borderless, semi-translucent titanium slate pill with rounded edges.
- Always on top (-topmost) with transparent background (-transparentcolor).
- Direct high-fidelity microphone recording with sounddevice + Whisper Large v3 Turbo (NO speech_recognition dependency).
- Global keyboard hook for Spacebar & hotkey detection using pynput.
- Press SPACE to speak, or click the notch!
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

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import requests
import numpy as np
import sounddevice as sd
import soundfile as sf
import io

from services.stt import WhisperSTTService
from services.vad import SileroVAD
from core.config import INPUT_SAMPLE_RATE, CHUNK_SIZE

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
        self.notch_w = 490
        self.notch_h = 64
        x = (screen_w - self.notch_w) // 2
        y = 14
        self.root.geometry(f"{self.notch_w}x{self.notch_h}+{x}+{y}")

        self.status = "idle"  # idle, listening, thinking, speaking
        self.current_text = "Press Space or Click to Speak"
        self.is_listening = False
        self.is_recording = False
        self.audio_frames = []
        self.stt_service = WhisperSTTService()
        self.vad_service = SileroVAD()

        # Build Canvas
        self.canvas = tk.Canvas(
            self.root,
            width=self.notch_w,
            height=self.notch_h,
            bg=self.transparent_key,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        # Click event to toggle listen
        self.canvas.bind("<Button-1>", lambda e: self.toggle_voice())

        # Draggable window capability
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.do_drag)
        self.drag_x = 0
        self.drag_y = 0

        self.draw_notch()
        self._start_global_space_listener()

    def _start_global_space_listener(self):
        """Starts background pynput listener so Spacebar works from anywhere."""
        from pynput import keyboard

        def on_press(key):
            try:
                if key == keyboard.Key.space:
                    # Only activate if currently idle
                    if not self.is_listening and not self.is_recording:
                        self.root.after(0, self.toggle_voice)
            except Exception:
                pass

        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()

    def start_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def do_drag(self, event):
        x = self.root.winfo_x() + (event.x - self.drag_x)
        y = self.root.winfo_y() + (event.y - self.drag_y)
        self.root.geometry(f"+{x}+{y}")

    def draw_notch(self):
        self.canvas.delete("all")
        w, h = self.notch_w, self.notch_h
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

        # Draw project header label: AUTONOMOUS AGENT
        self.canvas.create_text(
            46, 24,
            text="AUTONOMOUS AGENT",
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
        if self.is_listening or self.is_recording:
            self.is_recording = False
            self.is_listening = False
            self.set_status("idle", "Press Space or Click to Speak")
        else:
            self.is_listening = True
            self.is_recording = True
            self.set_status("listening", "Listening... (Speak naturally)")
            threading.Thread(target=self._record_audio_worker, daemon=True).start()

    def _record_audio_worker(self):
        """Records microphone PCM audio and transcribes with Whisper Large v3 Turbo."""
        try:
            self.audio_frames = []
            silence_count = 0
            max_silence = 25  # ~800ms of silence
            has_spoken = False

            def callback(indata, frames, time_info, status):
                if not self.is_recording:
                    raise sd.CallbackStop
                self.audio_frames.append(indata.copy())

            with sd.InputStream(
                samplerate=INPUT_SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback
            ):
                start_time = time.time()
                while self.is_recording:
                    sd.sleep(32)
                    if len(self.audio_frames) > 0:
                        last_chunk = self.audio_frames[-1].flatten()
                        is_speech = self.vad_service.is_speech(last_chunk, threshold=0.5)

                        if is_speech:
                            has_spoken = True
                            silence_count = 0
                        else:
                            if has_spoken:
                                silence_count += 1
                                if silence_count >= max_silence:
                                    # End of utterance detected!
                                    break

                    # Maximum 8 seconds per command
                    if time.time() - start_time > 8.0:
                        break

            self.is_recording = False
            if not self.audio_frames:
                self.root.after(0, lambda: self.set_status("idle", "Press Space or Click to Speak"))
                self.is_listening = False
                return

            self.root.after(0, lambda: self.set_status("thinking", "Transcribing..."))

            # Assemble PCM audio array
            pcm_array = np.concatenate(self.audio_frames, axis=0).flatten()

            # Transcribe via Groq Whisper Large v3 Turbo
            transcript = asyncio.run(self.stt_service.transcribe(pcm_array))

            if not transcript.strip():
                self.root.after(0, lambda: self.set_status("idle", "Press Space or Click to Speak"))
                self.is_listening = False
                return

            self.root.after(0, lambda: self.set_status("thinking", f'"{transcript}"'))

            # Dispatch prompt to FastAPI backend
            res = requests.post(
                f"{API_BASE}/api/chat",
                json={"prompt": transcript},
                timeout=25
            )
            data = res.json()
            response_text = data.get("response", "")
            audio_b64 = data.get("audio_base64")

            self.root.after(0, lambda: self.set_status("speaking", response_text))

            # Play audio synthesized by Edge-TTS
            if audio_b64:
                audio_bytes = base64.b64decode(audio_b64)
                data_np, sr_val = sf.read(io.BytesIO(audio_bytes))
                sd.play(data_np, sr_val)
                sd.wait()

            self.root.after(1000, lambda: self.set_status("idle", "Press Space or Click to Speak"))
            self.is_listening = False

        except Exception as e:
            err_msg = str(e)
            print(f"[Floating Notch Error]: {e}")
            self.root.after(0, lambda: self.set_status("idle", "Ready • Press Space to Speak"))
            self.is_listening = False
            self.is_recording = False


def launch_native_floating_notch():
    """Starts the native transparent desktop notch HUD."""
    app = FloatingNotchHUD()
    app.root.mainloop()


if __name__ == "__main__":
    launch_native_floating_notch()
