"""
Window State Awareness & Foreground Management for Windows.
Provides reliable discovery, restoring, and foreground focus for desktop applications
bypassing Windows OS focus stealing restrictions via thread input attachment.
"""

import time
import ctypes
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger("window_manager")

try:
    import win32gui
    import win32con
    import win32service
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


class WindowManager:
    """Manages active Windows desktop windows, focus switching, and window state awareness."""

    @staticmethod
    def _ensure_default_desktop():
        """Ensures the calling thread is attached to the user's interactive 'Default' desktop."""
        if not HAS_WIN32:
            return
        try:
            h_default = win32service.OpenDesktop("Default", 0, False, win32con.GENERIC_ALL)
            h_default.SetThreadDesktop()
        except Exception as e:
            logger.debug(f"Default desktop attachment notice: {e}")

    @classmethod
    def list_visible_windows(cls) -> List[Tuple[int, str]]:
        """
        Enumerates all visible top-level windows on the interactive Windows desktop.
        Returns a list of (hwnd, title) tuples.
        """
        if not HAS_WIN32:
            return []

        cls._ensure_default_desktop()
        windows: List[Tuple[int, str]] = []

        def enum_handler(hwnd: int, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                if title:
                    windows.append((hwnd, title))
            return True

        try:
            h_default = win32service.OpenDesktop("Default", 0, False, win32con.GENERIC_ALL)
            win32gui.EnumDesktopWindows(h_default, enum_handler, None)
        except Exception:
            # Fallback to standard EnumWindows
            try:
                win32gui.EnumWindows(enum_handler, None)
            except Exception:
                pass

        return windows

    @classmethod
    def find_window_by_keyword(cls, keyword: str) -> Optional[Tuple[int, str]]:
        """
        Searches for an active visible window matching keyword in its title.
        Returns (hwnd, title) or None.
        """
        kw = keyword.strip().lower()
        windows = cls.list_visible_windows()

        # 1. Exact match
        for hwnd, title in windows:
            if kw == title.lower():
                return hwnd, title

        # 2. Substring match
        for hwnd, title in windows:
            if kw in title.lower():
                return hwnd, title

        return None

    @classmethod
    def focus_and_foreground_window(cls, hwnd: int) -> bool:
        """
        Brings the target window to the absolute foreground:
        1. Restores window if minimized (SW_RESTORE).
        2. Attaches calling thread input to the target thread to bypass Windows focus lock.
        3. Calls SetForegroundWindow and BringWindowToTop.
        """
        if not HAS_WIN32 or not hwnd:
            return False

        try:
            cls._ensure_default_desktop()

            # 1. Restore if minimized
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            # 2. Attach thread input to bypass SetForegroundWindow restrictions
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            current_tid = kernel32.GetCurrentThreadId()
            target_tid = user32.GetWindowThreadProcessId(hwnd, None)

            attached = False
            if current_tid != target_tid and target_tid != 0:
                attached = bool(user32.AttachThreadInput(current_tid, target_tid, True))

            try:
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
            finally:
                if attached:
                    user32.AttachThreadInput(current_tid, target_tid, False)

            # Short settlement pause for OS window renderer
            time.sleep(0.15)
            return True
        except Exception as e:
            logger.error(f"Failed to focus window {hwnd}: {e}")
            return False

    @classmethod
    def wait_and_focus_window(cls, keyword: str, timeout_seconds: float = 3.0) -> Optional[Tuple[int, str]]:
        """
        Polls for a window matching keyword to appear within timeout, then focuses it.
        Ideal right after launching an application (e.g. calc.exe, notepad.exe).
        """
        start = time.time()
        while time.time() - start < timeout_seconds:
            found = cls.find_window_by_keyword(keyword)
            if found:
                hwnd, title = found
                cls.focus_and_foreground_window(hwnd)
                return hwnd, title
            time.sleep(0.2)
        return None


window_manager = WindowManager()
