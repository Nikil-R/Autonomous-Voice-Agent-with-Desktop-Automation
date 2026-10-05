"""
System Tray & Global Windows Hotkey Companion for Jarvis Autonomous Voice Agent.
Features:
- Native Windows System Tray icon with status menu (Open HUD, Toggle Voice, Vitals, Quit).
- Global OS Hotkey (Ctrl + Shift + Space) that pops up and focuses the floating HUD from ANY application.
- Auto-spawns browser app window if closed.
"""

import sys
import os
import time
import threading
import webbrowser
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
import pystray
from pynput import keyboard

# Ensure ApexCore root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from tools.window_manager import window_manager

FRONTEND_URL = "http://127.0.0.1:8000"


def create_tray_icon_image():
    """Generates an elegant glowing Jarvis circular icon for the Windows system tray."""
    image = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Outer cyan glowing ring
    draw.ellipse((4, 4, 60, 60), outline=(0, 240, 255, 255), width=4)
    # Inner glowing core
    draw.ellipse((16, 16, 48, 48), fill=(0, 160, 255, 220))
    # Center pulse dot
    draw.ellipse((26, 26, 38, 38), fill=(255, 255, 255, 255))
    return image


def focus_or_launch_hud():
    """Brings the Voice Dynamic Notch window to the absolute foreground or launches it."""
    # Look for existing browser window with Voice HUD
    found = window_manager.find_window_by_keyword("Voice")
    if not found:
        found = window_manager.find_window_by_keyword("Autonomous")

    if found:
        hwnd, title = found
        window_manager.focus_and_foreground_window(hwnd)
        print(f"⚡ [Global Hotkey] Focused existing Voice HUD: {title}")
    else:
        # Launch dedicated app-window mode in Chrome
        try:
            cmd = f'start chrome --app="{FRONTEND_URL}"'
            subprocess.Popen(cmd, shell=True)
            print("🚀 [Global Hotkey] Launched floating HUD window.")
            # Focus after short settlement
            window_manager.wait_and_focus_window("Voice", timeout_seconds=3.0)
        except Exception:
            webbrowser.open(FRONTEND_URL)


class GlobalHotkeyManager:
    """Manages system-wide global hotkey listener using pynput."""

    def __init__(self):
        self.listener = None
        # Track active keys for Ctrl + Shift + Space
        self.current_keys = set()

    def on_press(self, key):
        self.current_keys.add(key)
        # Check if Ctrl + Shift + Space is triggered
        ctrl_pressed = any(
            k in self.current_keys
            for k in [keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r]
        )
        shift_pressed = any(
            k in self.current_keys
            for k in [keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r]
        )
        space_pressed = key == keyboard.Key.space

        if ctrl_pressed and shift_pressed and space_pressed:
            threading.Thread(target=focus_or_launch_hud, daemon=True).start()

    def on_release(self, key):
        self.current_keys.discard(key)

    def start(self):
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.daemon = True
        self.listener.start()


def run_system_tray():
    """Runs the persistent Windows System Tray icon."""
    print("🌟 Starting Jarvis System Tray & Global Hotkey Engine...")
    print("👉 Global Hotkey: Press [Ctrl + Shift + Space] from ANY window to pop up Jarvis HUD.")

    # 1. Start Global Hotkey listener in background thread
    hotkey_mgr = GlobalHotkeyManager()
    hotkey_mgr.start()

    # 2. Build System Tray Menu
    icon_image = create_tray_icon_image()

    def on_open_hud(icon, item):
        focus_or_launch_hud()

    def on_exit(icon, item):
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Voice Agent HUD (Ctrl+Shift+Space)", on_open_hud, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open Notch in Chrome", lambda icon, item: webbrowser.open(FRONTEND_URL)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit Voice Agent", on_exit)
    )

    tray_icon = pystray.Icon(
        name="VoiceAgentHUD",
        icon=icon_image,
        title="Autonomous Voice Agent (Ctrl+Shift+Space)",
        menu=menu
    )

    tray_icon.run()


if __name__ == "__main__":
    run_system_tray()
