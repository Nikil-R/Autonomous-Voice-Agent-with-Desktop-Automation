"""
Multimodal Vision Grounding & Screen Action Controller for ApexCore.
Enables full computer use:
1. Fast screen capture via PyAutoGUI bound to Default user desktop.
2. Multimodal Vision analysis via Gemini Vision models (gemini-flash-lite-latest / gemini-flash-latest).
3. Visual element coordinate localization (x, y) for buttons, links, videos, or UI icons.
4. Precision mouse movement and clicking on visual targets.
"""

import io
import os
import re
import json
import time
import logging
from typing import Dict, Any, Optional, Tuple
from core.config import GEMINI_API_KEY

logger = logging.getLogger("vision_grounding")

try:
    import pyautogui
    import win32service
    import win32con
    HAS_GUI = True
except ImportError:
    HAS_GUI = False

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class VisionGroundingEngine:
    """Multimodal Vision Engine for desktop screen understanding and coordinate localization."""

    def __init__(self, api_key: str = GEMINI_API_KEY):
        self.api_key = api_key
        self.client = genai.Client(api_key=self.api_key) if (HAS_GENAI and self.api_key) else None
        self.candidate_models = [
            "gemini-2.5-flash",
            "gemini-flash-latest",
            "gemini-flash-lite-latest",
            "gemini-2.5-pro"
        ]

    @staticmethod
    def _ensure_desktop():
        """Binds the current thread to the interactive Windows user desktop for screen grab."""
        if not HAS_GUI:
            return
        try:
            h = win32service.OpenDesktop("Default", 0, False, win32con.GENERIC_ALL)
            h.SetThreadDesktop()
        except Exception:
            pass

    def capture_screenshot(self, quality: int = 80) -> Optional[Tuple[bytes, int, int]]:
        """
        Captures a fast JPEG screenshot of the primary Windows monitor.
        Returns (jpeg_bytes, width, height) or None.
        """
        if not HAS_GUI:
            return None

        try:
            self._ensure_desktop()
            img = pyautogui.screenshot()
            width, height = img.size

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            return buf.getvalue(), width, height
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None

    def analyze_screen(self, question_or_task: str = "Describe what is currently visible on the screen.") -> Dict[str, Any]:
        """
        Takes a screenshot and sends it to the Multimodal Vision Model for scene description or inspection.
        """
        if not self.client:
            return {"success": False, "message": "Gemini Vision client is not configured with an API key."}

        shot = self.capture_screenshot()
        if not shot:
            return {"success": False, "message": "Could not capture desktop screen."}

        jpeg_bytes, width, height = shot

        prompt = f"""
You are Jarvis, an ultra-fast multimodal AI desktop assistant.
Look at this screenshot of the user's computer screen ({width}x{height} pixels).
The user asks: "{question_or_task}"

Give a crisp, concise, high-impact answer in 1 or 2 spoken sentences.
Do NOT use asterisks, hashtags, or markdown formatting symbols.
"""
        last_err = None
        for model_name in self.candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"),
                        prompt
                    ]
                )
                text = response.text.strip() if response.text else "Unable to describe screen."
                return {
                    "success": True,
                    "resolution": f"{width}x{height}",
                    "model_used": model_name,
                    "message": text
                }
            except Exception as e:
                last_err = e
                continue

        return {"success": False, "message": f"Vision analysis failed: {str(last_err)}"}

    def locate_target_coordinates(self, target_description: str) -> Dict[str, Any]:
        """
        Uses the Multimodal Vision Model to find the exact pixel coordinates (x, y)
        of a UI element, button, link, or object on screen.
        """
        if not self.client:
            return {"found": False, "message": "Gemini Vision client is not configured."}

        shot = self.capture_screenshot()
        if not shot:
            return {"found": False, "message": "Could not capture screen for localization."}

        jpeg_bytes, width, height = shot

        prompt = f"""
You are an expert AI GUI computer use vision model.
Analyze this screenshot of the user's screen ({width}x{height} pixels).
The user wants to locate and click on: '{target_description}'.

Locate the center pixel coordinates (x, y) of the target element.
Return ONLY a valid JSON object strictly formatted as:
{{
  "found": true,
  "target": "{target_description}",
  "x": <integer x coordinate between 0 and {width}>,
  "y": <integer y coordinate between 0 and {height}>,
  "description": "<brief description of the matched element>"
}}

If the element is not visible or cannot be found, return:
{{
  "found": false,
  "message": "Target '{target_description}' is not visible on the current screen."
}}
Do NOT output markdown backticks (like ```json), output raw JSON only.
"""
        last_err = None
        for model_name in self.candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"),
                        prompt
                    ]
                )
                raw = response.text or ""
                clean_json = re.sub(r'```json\s*', '', raw)
                clean_json = re.sub(r'```\s*', '', clean_json).strip()
                data = json.loads(clean_json)
                data["model_used"] = model_name
                return data
            except Exception as e:
                last_err = e
                continue

        return {"found": False, "message": f"Localization failed: {str(last_err)}"}

    def click_on_visual_target(self, target_description: str, double_click: bool = False) -> Dict[str, Any]:
        """
        Multimodal Screen Grounding Action:
        1. Captures screen.
        2. Queries Vision model for center coordinates (x, y).
        3. Moves the mouse smoothly and clicks on the target.
        """
        coords_res = self.locate_target_coordinates(target_description)
        if not coords_res.get("found"):
            msg = coords_res.get("message") or f"Could not find '{target_description}' on screen."
            return {"success": False, "message": msg}

        x = int(coords_res["x"])
        y = int(coords_res["y"])

        if not HAS_GUI:
            return {"success": False, "message": f"Located '{target_description}' at ({x}, {y}), but GUI automation is unavailable."}

        try:
            self._ensure_desktop()
            # Smooth human-like cursor glide to coordinate
            pyautogui.moveTo(x, y, duration=0.3)
            if double_click:
                pyautogui.doubleClick(x, y)
            else:
                pyautogui.click(x, y)

            desc = coords_res.get("description") or target_description
            return {
                "success": True,
                "x": x,
                "y": y,
                "target": target_description,
                "message": f"Clicked on {desc} at position ({x}, {y}), Sir."
            }
        except Exception as e:
            return {"success": False, "message": f"Mouse action failed: {str(e)}"}


vision_engine = VisionGroundingEngine()
